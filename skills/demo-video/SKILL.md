---
name: demo-video
description: Make a 2–3 minute narrated product demo video from the real product. Plan the script and beats, film web apps with Playwright and desktop/Electron apps (e.g. Paratext 10) over a CDP screencast, generate documentary-style opening photos, cut it all together with ffmpeg from a JSON edit list (zooms, sped-up waits, overlays on spoken phrases, an end card with a QR code), voice drafts with free local Kokoro TTS and the final with ElevenLabs, and run review rounds with the user in FrameJam. Use when asked to make, script, record, edit, re-voice or revise a demo, walkthrough or promo video of an app or tool.
---

# Demo video

A narrated 2–3 minute demo built from the real product: screen recordings driven by script, a
few photos to open, a voiceover, and an end card. You do the recording, cutting and voicing; the
user reviews each version in FrameJam with comments pinned to moments in the video, and you apply
them and re-render. Faithbridge's and AQuA's videos (SIL, Oct 2026) took 12–14 rounds each, most
of them small.

The pipeline:

```
PLAN.md ──► scenes/*.json ──record.js──────► rec/sceneN/video.webm ─┐
            take.js ─────cdp-record.js─────► rec/take.mp4 ──────────┤
            photos.json ──OpenAI images────► rec/photos/*.png ──────┼─► edit.json ──assemble.py──► rec/rough-cut.mp4
            endcard.html, cards.html ───────────────────────────────┘         (Kokoro draft / ElevenLabs final)
                                                                                         │
                                         FrameJam review ◄── rec/renders/vN.mp4 ◄────────┘
```

## Setup

Make a folder for the video in the product's repo (for example `docs/demo-video/`) and copy in the
scripts and templates from this skill's folder:

```bash
SKILL=<this skill's folder>   # e.g. ~/.claude/skills/demo-video or ~/.agents/skills/demo-video
cp $SKILL/scripts/* $SKILL/templates/* docs/demo-video/
```

Keep recordings, renders and voice files out of git: use an output folder outside the repo (or a
gitignored one), called `rec/` below. Secrets go in a gitignored `.env`.

You need:

- **ffmpeg** and **Node** with Playwright (`npm i playwright && npx playwright install chromium`).
- **Python** with `soundfile pillow requests kokoro-onnx espeakng-loader` (the repo's venv or a new one).
- **Kokoro** model files for draft voices, in a folder you point `KOKORO_DIR` at:
  `kokoro-v1.0.onnx` and `voices-v1.0.bin` from
  `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/`.
- **ElevenLabs** `ELEVENLABS_API_KEY` for the final voice (see step 7).
- **OpenAI** `OPENAI_API_KEY` for the photos (step 4).
- **FrameJam** for reviews: `npx -y framejam@latest install`, then restart the agent. It provides
  the `framejam:start` skill and the MCP tools used in step 6.
- A **demo account** on the product with clean, shareable data (no personal data, nothing
  confidential, real outputs only).

## 1. Plan (`PLAN.md`)

Agree these with the user before recording anything, and keep `PLAN.md` as the running record:

- **Audience and purpose.** Who watches, what they already know, what they should do afterwards.
- **Length.** 2:30–3:00 is about 350–420 words of narration. Set a hard maximum.
- **Split.** Rough shares of time per feature ("a third each: X, Y, Z") — the user usually has a view.
- **Beats.** A table: time, beat, what's on screen, source (scene file, photo, card). The usual
  shape: the need (photos) → what the tool is (one sentence) → two or three concrete demos → reach
  → who built it and one call to action (end card).
- **Data.** Real, openly licensed or the team's own; every result on screen must be a real output.
  Note the attribution needed on the end card.
- **Script draft**, beat by beat.
- **Decisions log.** After every review round, add what the user decided ("say 'outside experts',
  not 'consultants'") so later rounds don't undo it.

Read `lessons.md` in this skill before writing the script: it is what the review rounds taught us.

## 2. Record web scenes (`record.js`)

A scene is one continuous take, written as JSON steps (`scene.example.json`): `goto`, `click`,
`clickText`, `type` (typed at a natural speed), `scroll`, `scrollTo`, `move`, `hold`,
`screenshot`. The recorder logs in off camera, glides the mouse like a person, records at
1600×900 and writes `video.webm`, `timeline.json` (when each step started: use these times to cut)
and the screenshots.

```bash
node record.js scenes/01-search.json rec/scene1 --no-video   # probe: try inputs, look at the screenshots
node record.js scenes/01-search.json rec/scene1              # record
```

- **Probe before recording.** Try several candidate inputs (questions, verses, chapters) with
  `--no-video`, read the results, and pick ones a non-specialist can follow. Check that anything
  you'll narrate is actually correct (look the data up, don't trust the screen).
- **Undo changes off camera** at the end of the scene (restore a dismissed item, delete a test
  entry) and say so in the scene's `about`.
- **Watch the recording** (extract frames with ffmpeg and look at them) for loading spinners, white
  flashes, tooltips, banners, personal data, and anything stale.
- Record a bit long: cutting is cheap, re-recording isn't.

## 3. Record a desktop app (`cdp-record.js`)

For Electron apps (Paratext 10 Studio, Platform.Bible) or anything with a DevTools port, drive it
with Playwright over CDP and record the page with a CDP screencast: no screen recorder, nothing
outside the window, no notifications.

```bash
<app> --remote-debugging-port=9229                                    # start the app
node cdp-record.js take.js rec/desk --page isMainWindow --prep         # put it in its starting state; check rec/desk/prep.png
node cdp-record.js take.js rec/desk --page isMainWindow                # film the take
python frames2mp4.py rec/desk/cast rec/desk-take.mp4 "crop=1896:970:0:70,scale=1600:-2,pad=1600:900:0:(oh-ih)/2:color=white"
```

`take.example.js` shows the shape: find the panel's iframe, `mark()` each moment you'll cut on,
park the pointer off to the side so it doesn't raise tooltips, and blur focus before starting
(a focused button shows its tooltip in the first seconds). Work out the crop from a screenshot.

- Ask the user to set the app up (right account/registry, project, light or dark theme, panes),
  and to clear anything they don't want shown. Tell them what you'll click before you click it.
- **Hover answers and buttons; don't click ones that change real data** or spend a quota (runs,
  credits). Toggles (expanders, "show more") keep their state between takes: check before clicking.
- Before recording, list the frames' text (`frame.evaluate(() => document.body.innerText)`) to
  find selectors, and take screenshots to check state.

## 4. Opening photos

Two or three candid documentary photos of the people the tool is for, generated with the OpenAI
Images API. Keep the prompts in `photos.json` (`photos.example.json` has three that worked):
the place and people specifically, modern equipment, a real lens and light ("35mm, f/2.8, natural
daylight, clean low-noise image, no film grain"), "no readable text, no logos", and "authentic,
unposed, not stock-photo cheerful".

```python
import base64, json, pathlib
from openai import OpenAI
client = OpenAI()
for name, prompt in json.load(open("photos.json")).items():
    r = client.images.generate(model="gpt-image-1.5", prompt=prompt, size="1536x1024")
    pathlib.Path(f"rec/photos/{name}.png").write_bytes(base64.b64decode(r.data[0].b64_json))
```

Look at every photo: expect re-rolls (grain, odd hands, scruffy subjects, wrong region, someone
presiding over the others). Show the user the picks before the first cut.

## 5. Cut (`edit.json` → `assemble.py`)

`edit.json` (`edit.example.json`) holds the script and the cut list. `clips` names the sources
(relative to the output folder; `.html` ones are relative to `edit.json` and rendered fresh each
run). Each beat has:

- `vo`: the narration as written (it becomes the transcript). `say` (optional): what the voice is
  given instead, to fix pronunciation ("S I L", "Aqua" for "AQuA") or add a pause
  (`<break time="0.3s" />`). Keep both in step.
- `segments`: `{clip, from, to}` in seconds of the clip, plus optionally
  - `speed`: play faster (1.15–1.6 is invisible for UI; slow down rather than hold a frame).
  - `flex: true`: a wait (an answer loading) sped up just enough for the beat to fit its narration,
    up to `maxFlex`.
  - `zoom: {z, cx, cy, ease, in, out}`: push in to `z` on the point (`cx`, `cy` as fractions of the
    frame) over `ease` seconds, and back out at the end unless `out: false`. `in: false` starts
    zoomed, to carry a zoom across segments. Photos get a slow push (`z` 1.08, `ease` = length).
- `leadIn`: seconds of picture before the narration starts (default 0.3).
- `overlay`: `{html, layers: {layer: time or "phrase"}, to}`: each `[data-layer]` element of the
  page (`cards.html`) fades in when its phrase is spoken.

```bash
KOKORO_DIR=~/.cache/kokoro python assemble.py edit.json rec --draft
```

It prints each beat's start, length, narration length, wait speed and silence, and writes
`rec/rough-cut.mp4`, `rec/cut.json` and `rec/transcript.json`. A beat whose footage is shorter than
its narration holds the last frame (`heldFrame` in `cut.json`): fix it with slower segments or
more footage. Keep silences under about 0.7 s inside a section.

Look at the result before showing it: extract a frame from each beat
(`ffmpeg -ss T -i rec/rough-cut.mp4 -frames:v 1 f.png`) and check the total length.

## 6. Review in FrameJam

Each render is a version: copy it to `rec/renders/vN.mp4` with `rec/renders/vN.transcript.json`
(from `rec/transcript.json`) so the user can comment on the words as well as the picture.

1. First version: `open_review` with `videoPath` and `transcriptPath`, then open the URL for the
   user (FrameJam runs at http://localhost:2400; `npx -y framejam start` if it doesn't load).
2. `wait_for_feedback`, and call it again while it returns `pending`; after 12 pending results in
   a row (about 10 minutes), stop and tell the user to press **Finish review** and say "apply my
   FrameJam feedback" (then call `get_feedback`).
3. Apply every comment. Re-render (`--draft`), copy to `vN+1`, `add_version` with a short note that
   says what changed for each comment, and wait again.
4. When a comment is a question or a judgment call, answer it in the version note or ask in chat;
   don't silently skip it. Record decisions in `PLAN.md`.

Rounds use the Kokoro draft voice so they cost nothing. Switch to ElevenLabs once the words are
settled.

## 7. Final voice (ElevenLabs)

Add to `edit.json`:

```json
"elevenlabs": { "voice": "XrExE9yKIg1WjnnlVkGX", "model": "eleven_multilingual_v2" }
```

and run `assemble.py` without `--draft` (with `ELEVENLABS_API_KEY` in the environment or `.env`).
That voice is Matilda; use the same one across a series of videos so they feel like a set. The
`/with-timestamps` endpoint returns character timings, which give exact overlay cues and a
word-level transcript.

- **Cost:** one credit per character of `say`, so a 400-word video is about 2,500 credits. Each
  line is cached in `rec/vo/` by its text, so re-renders are free and changing one line re-voices
  only that line.
- **Plan:** the Free tier has no commercial licence and only 10k credits a month. Starter (30k a
  month, commercial licence, often $1 for the first month) covers two or three videos with
  re-takes; cancel before it renews if it's a one-off. Check current prices.
- A key without the `user_read` permission can't read its balance; a "quota exceeded" error right
  after upgrading usually clears on retry a minute later.
- **Listen to every line.** Fix mispronunciations in `say` (spell acronyms out, or not: "A I"
  left an audible gap, "AI" was right), then put the final render up as a FrameJam version too.

## 8. End card and QR code

`endcard.html` holds the name, a one-line tag, the call to action with the URL, a QR code for it
(viewers often have their phone to hand), the credit, and any Scripture attribution. Make the QR
code and check it decodes from the rendered video, not just the SVG:

```python
import qrcode, qrcode.image.svg
qrcode.make("https://example.org/tool", image_factory=qrcode.image.svg.SvgPathImage, border=0).save("qr.svg")
```

```bash
ffmpeg -sseof -3 -i rec/rough-cut.mp4 -frames:v 1 end.png && zbarimg end.png
```

## Finishing

Check the final file: length (`ffprobe`), no silence over about 1.5 s, the last frame, the QR code,
and that the narration matches the transcript. Leave any data the demo changed as it was, and tell
the user where the file is (copy it out of temporary folders). Offer to commit the video folder
(scripts, scenes, `edit.json`, `PLAN.md`), never the recordings or `.env`.
