#!/usr/bin/env python3
"""Burn action captions ("tap X", "swipe up on space", "type: hello") into a test recording.

Works for any platform: the test script logs each action with a timestamp, then this tool
overlays the captions on the video. Needs Pillow and ffmpeg (no libass/drawtext required).

    caption_video.py start  LOG                 # call right after the recorder is running
    caption_video.py log    LOG "swipe up on space"
    caption_video.py render VIDEO LOG OUT [--offset S] [--pos top|bottom|middle]

LOG is JSONL: a {"start": epoch} line, then {"t": seconds_since_start, "text": "..."} lines.
Scripts that already know their own timestamps can write the {"t", "text"} lines directly.
--offset shifts every caption (seconds; positive = later) to absorb recorder start-up lag.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
MIN_DUR, MAX_DUR = 0.9, 2.2


def cmd_start(log):
    with open(log, "w") as f:
        f.write(json.dumps({"start": time.time()}) + "\n")


def cmd_log(log, text):
    with open(log) as f:
        start = json.loads(f.readline())["start"]
    with open(log, "a") as f:
        f.write(json.dumps({"t": round(time.time() - start, 3), "text": text}, ensure_ascii=False) + "\n")


def probe_size(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", video,
    ]).decode().strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_caption(text, video_w, path):
    f = font(max(18, video_w // 24))
    pad_x, pad_y = video_w // 40, video_w // 70
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    w = min(video_w - 2 * pad_x, tw + 2 * pad_x)
    h = th + 2 * pad_y
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(20, 20, 20, 215), outline=(255, 200, 0, 255), width=max(2, video_w // 400))
    d.text(((w - tw) // 2 - box[0], pad_y - box[1]), text, font=f, fill=(255, 255, 255, 255))
    img.save(path)
    return w, h


def cmd_render(video, log, out, offset=0.0, pos="top"):
    with open(log) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    acts = sorted((r for r in rows if "t" in r), key=lambda r: r["t"])
    if not acts:
        sys.exit("no actions in log")
    vw, vh = probe_size(video)
    tmp = tempfile.mkdtemp(prefix="captions-")
    inputs, chain, last = [], [], "0:v"
    for i, a in enumerate(acts):
        t = max(0.0, a["t"] + offset)
        nxt = acts[i + 1]["t"] + offset if i + 1 < len(acts) else t + MAX_DUR
        end = max(t + MIN_DUR, min(nxt, t + MAX_DUR))
        png = os.path.join(tmp, f"c{i}.png")
        w, h = render_caption(a["text"], vw, png)
        y = {"top": vh // 12, "middle": (vh - h) // 2, "bottom": vh - h - vh // 12}[pos]
        inputs += ["-i", png]
        tag = f"v{i}"
        chain.append(f"[{last}][{i + 1}:v]overlay=x=(W-w)/2:y={y}:enable='between(t,{t:.3f},{end:.3f})'[{tag}]")
        last = tag
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-i", video, *inputs,
        "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-c:a", "copy", out,
    ], check=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "start":
        cmd_start(a[1])
    elif len(a) >= 3 and a[0] == "log":
        cmd_log(a[1], " ".join(a[2:]))
    elif len(a) >= 4 and a[0] == "render":
        opts = dict(zip(a[4::2], a[5::2]))
        cmd_render(a[1], a[2], a[3], float(opts.get("--offset", 0)), opts.get("--pos", "top"))
    else:
        sys.exit(__doc__)
