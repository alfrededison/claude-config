"""Burn touch markers into a test recording (shared by ios_record_test.py and android_record_test.py).

A test prints one line before each action:
    TOUCH_TAP   <epoch> <x> <y> <screenW> <screenH>
    TOUCH_SWIPE <epoch> <x1> <y1> <x2> <y2> <screenW> <screenH>
(POC_TAP / POC_SWIPE are accepted too.) Points are in the screen's own coordinate space and
are scaled to the video size. Taps get an orange square, swipes a dotted path whose dots grow
toward the end, so the direction is visible.

Simulator/device recorders write a frame only when the screen changes, so the clip is
re-encoded at a constant 30 fps with its last frame held until the run ended; otherwise
markers on a still screen and the still tail of the run would be missing.
"""
import json
import re
import subprocess
from pathlib import Path

N = r"(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)"  # also accepts exponents, e.g. Kotlin's 1.7636E9
TAP = re.compile(rf"(?:TOUCH|POC)_TAP {N} {N} {N} {N} {N}")
SWIPE = re.compile(rf"(?:TOUCH|POC)_SWIPE {N} {N} {N} {N} {N} {N} {N}")


def parse(text: str, clock_offset: float = 0.0):
    """Return (taps, swipes) from log text; clock_offset is subtracted from each epoch
    (use it when the lines were stamped by a device clock that differs from the host's)."""
    taps = [(t - clock_offset, *rest) for t, *rest in (tuple(map(float, m)) for m in TAP.findall(text))]
    swipes = [(t - clock_offset, *rest) for t, *rest in (tuple(map(float, m)) for m in SWIPE.findall(text))]
    return taps, swipes


def burn(clip: Path, taps, swipes, started: float, total: float):
    """Re-encode clip in place at 30 fps, `total` seconds long, with markers drawn.
    `started` is the host epoch of the clip's first frame."""
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(clip)], text=True))
    vw, vh = probe["streams"][0]["width"], probe["streams"][0]["height"]
    box = round(vw * 0.08)              # tap square, ~8% of the width
    thick = max(4, round(vw * 0.008))
    f = [f"fps=30,tpad=stop_mode=clone:stop_duration={total:.2f}"]
    for t, x, y, sw, sh in taps:
        s = max(0.0, t - started)
        px, py = x * vw / sw, y * vh / sh
        f.append(f"drawbox=x={px - box / 2:.0f}:y={py - box / 2:.0f}:w={box}:h={box}"
                 f":color=orange@0.9:t={thick}:enable='between(t,{s:.3f},{s + 0.8:.3f})'")
    for t, x1, y1, x2, y2, sw, sh in swipes:
        s = max(0.0, t - started)
        en = f"enable='between(t,{s:.3f},{s + 1.0:.3f})'"
        ax, ay, bx, by = x1 * vw / sw, y1 * vh / sh, x2 * vw / sw, y2 * vh / sh
        n = 12
        for i in range(n + 1):  # dots from start to end, growing: shows the direction
            k = i / n
            d = round(thick * 2 + k * box * 0.5)
            cx, cy = ax + (bx - ax) * k, ay + (by - ay) * k
            f.append(f"drawbox=x={cx - d / 2:.0f}:y={cy - d / 2:.0f}:w={d}:h={d}:color=orange@0.9:t=fill:{en}")
    tmp = clip.with_suffix(".cfr.mp4")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf", ",".join(f), "-t", f"{total:.2f}",
                        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(tmp)], check=True)
        tmp.replace(clip)
    finally:
        tmp.unlink(missing_ok=True)
