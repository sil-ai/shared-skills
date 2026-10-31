"""Turn a CDP screencast folder (frames.json + fNNNNN.jpg, from cdp-record.js) into a 30 fps mp4.

    python frames2mp4.py CAST_DIR OUT.mp4 [FILTER]

The screencast only sends a frame when the page changes, so each frame is held
until the next one. Time 0 is the start of the take, so the timestamps in
timeline.json line up with the video. FILTER is an ffmpeg filter for cropping
and fitting the window to 1600x900, for example
    "crop=1896:970:0:70,scale=1600:-2,pad=1600:900:0:(oh-ih)/2:color=white"
"""

import json
import subprocess
import sys

d, out = sys.argv[1], sys.argv[2]
crop = sys.argv[3] if len(sys.argv) > 3 else "scale=1600:900:force_original_aspect_ratio=decrease,pad=1600:900:(ow-iw)/2:(oh-ih)/2"
m = json.load(open(f"{d}/frames.json"))
fr = m["frames"]
if not fr:
    sys.exit(f"No frames were captured in {d}")
t0 = m["wallStart"]
lines = []
for i, f in enumerate(fr):
    start = t0 if i == 0 else f["t"]  # hold the first frame from the start of the take
    end = fr[i + 1]["t"] if i + 1 < len(fr) else f["t"] + 1.0
    lines += [f"file 'f{f['n']:05d}.jpg'", f"duration {max(end - start, 0.001):.4f}"]
lines.append(f"file 'f{fr[-1]['n']:05d}.jpg'")
open(f"{d}/list.txt", "w").write("\n".join(lines) + "\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{d}/list.txt",
                "-vf", f"{crop},fps=30", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out], check=True)
print(f"{out}: first frame {fr[0]['t'] - t0:.2f}s after the take started")
