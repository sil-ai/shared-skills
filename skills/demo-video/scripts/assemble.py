"""Assemble a rough cut of the demo video from recorded clips and a generated voiceover.

    python assemble.py edit.json OUT_DIR [--draft]

--draft uses the local Kokoro voice even when ElevenLabs is configured, so review
rounds don't spend ElevenLabs credits.

OUT_DIR must already hold the recordings named in edit.json "clips" (paths are
relative to OUT_DIR, as written by record.js / cdp-record.js). A clip ending in
.html (an end card, a title card) is relative to edit.json instead, and is
rendered to a 1600x900 still on every run, so edits to it always show. Writes:
  vo/NN.wav       the voiceover for each beat
  rough-cut.mp4   the assembled video with voiceover
  cut.json        each beat's start time, length and the speed used for waits
  transcript.json the voiceover's timings (per word with ElevenLabs, per beat with Kokoro),
                  in the words of "vo" (with ElevenLabs, of "say" when the two differ in word count)

Each beat plays its segments in order. A segment marked "flex" (usually the
wait for an answer) is sped up just enough for the beat to fit its voiceover,
up to MAX_FLEX times (or edit.json "maxFlex"); if the footage is still shorter than the voiceover, the
beat's last frame is held.

A segment can carry "zoom": {"z": 1.6, "cx": 0.6, "cy": 0.2} to push in on a
point (cx, cy as fractions of the frame); it eases in and back out over
"ease" seconds (default 0.6), or holds the zoom to the end with "out": false; "in": false
starts already zoomed in, to carry a zoom on from the segment before.
Image clips (.png) fill the frame. A beat's "leadIn" (default LEAD_IN) is the picture
before its voiceover starts. A beat's "overlay" lays the [data-layer]
elements of an HTML page (relative to edit.json) over it (rendered by render-layers.js), each fading in
at its time in "layers" and all fading out at "to". A time is seconds into the
beat's voiceover, or a phrase of it ("say" if given): the moment it is spoken.

The voice comes from ElevenLabs when edit.json has "elevenlabs": {"voice": ID,
"model": ...} and ELEVENLABS_API_KEY is set (in the environment, or a .env in the
current directory or next to edit.json); each line is cached in vo/ so
re-renders don't pay for it again. Otherwise it is a local stand-in (Kokoro, from
https://github.com/thewh1teagle/kokoro-onnx; set KOKORO_DIR to the folder with
kokoro-v1.0.onnx and voices-v1.0.bin), whose phrase times are estimates.
"""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import soundfile as sf

FPS = 30
SIZE = "1600:900"
MAX_FLEX = 12.0
LEAD_IN = 0.3  # seconds of picture before each beat's voiceover starts
TAIL = 0.5  # seconds of picture after it ends
HERE = Path(__file__).resolve().parent


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        sys.exit(f"{' '.join(args)}\n{result.stderr[-2000:]}")


def tts(beats, voice, speed, vo_dir):
    # Returns (wav, seconds, timings) for each beat; timings is None, or the spoken
    # characters and when each starts.
    import espeakng_loader
    from kokoro_onnx import EspeakConfig, Kokoro

    kdir = Path(os.environ.get("KOKORO_DIR", "."))
    # Point espeak-ng at the data bundled with espeakng_loader; its compiled-in default
    # is a path on the machine that built the wheel.
    espeak = EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=espeakng_loader.get_data_path())
    kokoro = Kokoro(str(kdir / "kokoro-v1.0.onnx"), str(kdir / "voices-v1.0.bin"), espeak_config=espeak)
    paths = []
    for i, beat in enumerate(beats):
        text = re.sub(r"<[^>]*>", " ", beat.get("say", beat["vo"]))  # Kokoro reads SSML tags aloud
        samples, rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        path = vo_dir / f"{i:02d}.wav"
        sf.write(path, samples, rate)
        paths.append((path, len(samples) / rate, None))
    return paths


def tts_elevenlabs(beats, config, vo_dir):
    import requests

    paths = []
    for i, beat in enumerate(beats):
        body = {"text": beat.get("say", beat["vo"]), "model_id": config.get("model", "eleven_multilingual_v2")}
        if "settings" in config:
            body["voice_settings"] = config["settings"]
        key = hashlib.sha256(json.dumps([config["voice"], body], sort_keys=True).encode()).hexdigest()[:12]
        cached = vo_dir / f"{key}.json"  # keyed by text only, so adding or moving a beat doesn't re-voice the others
        if not cached.exists():
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{config['voice']}/with-timestamps",
                              params={"output_format": "mp3_44100_128"}, json=body, timeout=300,
                              headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]})
            if not r.ok:
                sys.exit(f"ElevenLabs failed for beat {i}: {r.status_code} {r.text[:500]}")
            cached.write_text(json.dumps(r.json()))
        reply = json.loads(cached.read_text())
        mp3 = vo_dir / f"{i:02d}.mp3"
        mp3.write_bytes(base64.b64decode(reply["audio_base64"]))
        path = vo_dir / f"{i:02d}.wav"
        run("ffmpeg", "-y", "-i", str(mp3), str(path))
        alignment = reply["alignment"]
        paths.append((path, duration(path), ("".join(alignment["characters"]), alignment["character_start_times_seconds"])))
    return paths


def cue(at, text, vo_len, timings):
    # A layer time: seconds, or when a phrase of the voiceover starts (estimated from
    # its place in the text when there are no timings).
    if not isinstance(at, str):
        return at
    if not timings:
        text = re.sub(r"<[^>]*>", "", text)  # Kokoro doesn't speak the tags, so don't count them
    if at not in (timings[0] if timings else text):
        sys.exit(f"Overlay cue {at!r} is not in the narration: {text!r}")
    if timings:
        return timings[1][timings[0].index(at)]
    return vo_len * text.index(at) / len(text)


def words(timings, offset):
    text, starts = timings
    text = re.sub(r"<[^>]*>", lambda m: " " * len(m.group()), text)  # drop <break> tags
    out, begin = [], None
    for i, ch in enumerate(text + " "):
        if ch != " " and begin is None:
            begin = i
        elif ch == " " and begin is not None:
            end = starts[i] if i < len(starts) else starts[-1] + 0.3
            out.append({"text": text[begin:i], "start": round(offset + starts[begin], 2), "end": round(offset + end, 2)})
            begin = None
    return out


def zoom_level(zoom, t, length):
    # Eases 1 -> z over "ease" seconds (and back out at the end unless "out" is false).
    ease = max(zoom.get("ease", 0.6), 0.01)
    r = min(1.0, t / ease) if zoom.get("in", True) else 1.0
    if zoom.get("out", True):
        r = min(r, (length - t) / ease)
    r = max(0.0, r)
    return 1 + (zoom["z"] - 1) * r * r * (3 - 2 * r)


def zoom_frames(decode, zoom, length, out):
    # Zoom in Python with sub-pixel affine resampling: ffmpeg's scale+crop moves in whole
    # pixels, which makes slow zooms shimmer.
    from PIL import Image

    w, h = 1600, 900
    src = subprocess.Popen([*decode, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    dst = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", str(FPS), "-i", "-", "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                            str(out)], stdin=subprocess.PIPE)
    # The final window is centred on (cx, cy) as far as the frame edges allow; every
    # frame zooms about the one fixed point that lands on it, so the picture never
    # drifts sideways on the way in.
    zf = zoom["z"]
    x0f = min(max(zoom["cx"] * w - w / 2 / zf, 0), w - w / zf)
    y0f = min(max(zoom["cy"] * h - h / 2 / zf, 0), h - h / zf)
    n = 0
    while frame := src.stdout.read(w * h * 3):
        z = zoom_level(zoom, n / FPS, length)
        x0 = x0f * (1 - 1 / z) / (1 - 1 / zf)
        y0 = y0f * (1 - 1 / z) / (1 - 1 / zf)
        img = Image.frombytes("RGB", (w, h), frame)
        dst.stdin.write(img.transform((w, h), Image.AFFINE, (1 / z, 0, x0, 0, 1 / z, y0), Image.BICUBIC).tobytes())
        n += 1
    dst.stdin.close()
    if src.wait() or dst.wait():
        sys.exit(f"zoom failed for {out}")


def render_segment(src, seg, speed, out):
    length = (seg["to"] - seg["from"]) / speed
    if src.suffix == ".png":
        cmd = ["ffmpeg", "-v", "error", "-loop", "1", "-i", str(src), "-t", str(length),
               "-vf", f"scale={SIZE}:force_original_aspect_ratio=increase,crop={SIZE},fps={FPS}"]
    else:
        # Trim inside the filter chain, before setpts: an output -ss/-to would
        # apply to the sped-up timestamps and cut the wrong stretch.
        cmd = ["ffmpeg", "-v", "error", "-i", str(src), "-an",
               "-vf", f"trim=start={seg['from']}:end={seg['to']},setpts=(PTS-STARTPTS)/{speed},scale={SIZE},fps={FPS}"]
    if seg.get("zoom", {}).get("z", 1) > 1:
        zoom_frames(cmd, seg["zoom"], length, out)
        return
    cmd[-1] += ",format=yuv420p"
    run(*cmd, "-y", "-c:v", "libx264", "-preset", "veryfast", str(out))


def add_overlay(beat_file, overlay, layer_dir, out):
    run("node", str(HERE / "render-layers.js"), str(overlay["html"]), str(layer_dir))
    inputs, chains, last = [], [], "0:v"
    for k, (layer, at) in enumerate(overlay["layers"].items(), start=1):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(overlay["to"] + 0.5), "-i", str(layer_dir / f"{layer}.png")]
        chains.append(f"[{k}:v]format=rgba,fade=in:st={at}:d=0.35:alpha=1,"
                      f"fade=out:st={overlay['to'] - 0.35}:d=0.35:alpha=1[l{k}];[{last}][l{k}]overlay=eof_action=pass[o{k}]")
        last = f"o{k}"
    run("ffmpeg", "-y", "-i", str(beat_file), *inputs, "-filter_complex", ";".join(chains) + f";[{last}]format=yuv420p[v]",
        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", str(out))


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True)
    return float(out.stdout)


def main(edit_file, out_dir):
    edit = json.loads(Path(edit_file).read_text())
    out = Path(out_dir)
    work = out / "cut"
    vo_dir = out / "vo"
    work.mkdir(parents=True, exist_ok=True)
    vo_dir.mkdir(exist_ok=True)
    edit_dir = Path(edit_file).resolve().parent
    clips = {}
    for k, v in edit["clips"].items():
        if v.endswith(".html"):
            clips[k] = work / f"{k}.png"
            run("node", str(HERE / "render-layers.js"), str(edit_dir / v), str(clips[k]), "--card")
        else:
            clips[k] = out / v

    max_flex = edit.get("maxFlex", MAX_FLEX)
    for dotenv in (Path.cwd() / ".env", edit_dir / ".env"):
        if not os.environ.get("ELEVENLABS_API_KEY") and dotenv.exists():
            for line in dotenv.read_text().splitlines():
                line = line.removeprefix("export ")
                if line.startswith("ELEVENLABS_API_KEY="):
                    os.environ["ELEVENLABS_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")
    if "elevenlabs" in edit and "--draft" not in sys.argv:
        if not os.environ.get("ELEVENLABS_API_KEY"):
            sys.exit("edit.json asks for ElevenLabs but ELEVENLABS_API_KEY is not set; pass --draft for the Kokoro voice.")
        vo = tts_elevenlabs(edit["beats"], edit["elevenlabs"], vo_dir)
    else:
        vo = tts(edit["beats"], edit.get("voice", "af_heart"), edit.get("voiceSpeed", 1.0), vo_dir)
    beat_files, report, transcript, t = [], [], [], 0.0
    for i, (beat, (vo_path, vo_len, timings)) in enumerate(zip(edit["beats"], vo)):
        segs = beat["segments"]
        fixed = sum((s["to"] - s["from"]) / s.get("speed", 1.0) for s in segs if not s.get("flex"))
        flex = sum(s["to"] - s["from"] for s in segs if s.get("flex"))
        lead_in = beat.get("leadIn", LEAD_IN)
        target = max(lead_in + vo_len + TAIL, fixed + flex / max_flex)
        flex_speed = min(max_flex, max(1.0, flex / (target - fixed))) if flex else 1.0
        parts = []
        for j, seg in enumerate(segs):
            part = work / f"{i:02d}-{j:02d}.mp4"
            render_segment(clips[seg["clip"]], seg, flex_speed if seg.get("flex") else seg.get("speed", 1.0), part)
            parts.append(part)
        listing = work / f"{i:02d}.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
        joined = work / f"{i:02d}-joined.mp4"
        run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined))
        length = duration(joined)
        beat_file = work / f"{i:02d}-beat.mp4"
        hold = max(0.0, target - length)
        run("ffmpeg", "-y", "-i", str(joined), "-vf", f"tpad=stop_mode=clone:stop_duration={hold:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", str(beat_file))
        if "overlay" in beat:
            overlaid = work / f"{i:02d}-overlay.mp4"
            text = beat.get("say", beat["vo"])
            overlay = {**beat["overlay"], "html": edit_dir / beat["overlay"]["html"], "to": lead_in + cue(beat["overlay"]["to"], text, vo_len, timings),
                       "layers": {k: lead_in + cue(v, text, vo_len, timings) for k, v in beat["overlay"]["layers"].items()}}
            add_overlay(beat_file, overlay, work / f"{i:02d}-layers", overlaid)
            beat_file = overlaid
        length = duration(beat_file)
        beat_files.append(beat_file)
        report.append({"beat": beat["name"], "start": round(t, 2), "length": round(length, 2),
                       "voiceover": round(vo_len, 2), "waitSpeed": round(flex_speed, 1), "heldFrame": round(hold, 2),
                       "silence": round(length - vo_len - lead_in, 2), "leadIn": lead_in})
        if timings:
            spoken = words(timings, t + lead_in)
            written = beat["vo"].split()
            if len(written) == len(spoken):  # show the written words, not "say"'s spellings ("S I L")
                spoken = [{**w, "text": v} for w, v in zip(spoken, written)]
            transcript += spoken
        else:
            transcript.append({"text": beat["vo"], "start": round(t + lead_in, 2), "end": round(t + lead_in + vo_len, 2)})
        t += length

    listing = work / "all.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in beat_files))
    picture = work / "picture.mp4"
    run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(picture))

    inputs, chains = [], []
    for k, ((path, _, _), r) in enumerate(zip(vo, report)):
        inputs += ["-i", str(path)]
        ms = int((r["start"] + r["leadIn"]) * 1000)
        chains.append(f"[{k + 1}:a]adelay={ms}|{ms}[a{k}]")
    mix = ";".join(chains) + ";" + "".join(f"[a{k}]" for k in range(len(vo))) + \
        f"amix=inputs={len(vo)}:normalize=0[vo]"
    run("ffmpeg", "-y", "-i", str(picture), *inputs, "-filter_complex", mix, "-map", "0:v", "-map", "[vo]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out / "rough-cut.mp4"))
    (out / "cut.json").write_text(json.dumps(report, indent=2))
    (out / "transcript.json").write_text(json.dumps(transcript, indent=1))
    for r in report:
        print(f"{r['start']:6.1f}s  {r['length']:5.1f}s  vo {r['voiceover']:4.1f}s  wait x{r['waitSpeed']:<4}  silence {r['silence']:4.1f}s  {r['beat']}")
    print(f"Total {t:.1f}s -> {out / 'rough-cut.mp4'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit("usage: python assemble.py edit.json OUT_DIR [--draft]")
    main(*args)
