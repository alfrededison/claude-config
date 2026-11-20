#!/usr/bin/env python3
"""Tap or swipe on an Android device and log it, so android_record_test.py can mark it.

    adb_touch.py tap X Y
    adb_touch.py swipe X1 Y1 X2 Y2 [MS]      # default 300 ms
    adb_touch.py hold X Y [MS]               # long press, default 800 ms; marked as a tap

Use it instead of `adb shell input tap/swipe` in scripts run under android_record_test.py.
Coordinates are display pixels, the same as `adb shell input`. Targets $ANDROID_SERIAL
(android_record_test.py sets it). Prints a TOUCH_TAP / TOUCH_SWIPE line to stdout first.
Set TOUCH_SCREEN=WxH (in the current orientation) to skip the screen-size lookup on each call.
"""
import os
import re
import subprocess
import sys
import time


def adb():
    s = os.environ.get("ANDROID_SERIAL")
    return ["adb", "-s", s] if s else ["adb"]


def screen_size():
    if os.environ.get("TOUCH_SCREEN"):
        w, h = os.environ["TOUCH_SCREEN"].lower().split("x")
        return w, h
    # `cur=` follows the current rotation, like `input` coordinates and screenrecord's video;
    # `wm size` always reports the natural (portrait) size, so it is only a fallback.
    out = subprocess.check_output(adb() + ["shell", "dumpsys", "window", "displays"], text=True)
    m = re.search(r"\bcur=(\d+)x(\d+)", out)
    if m:
        return m.groups()
    out = subprocess.check_output(adb() + ["shell", "wm", "size"], text=True)
    sizes = dict(re.findall(r"(Physical|Override) size: (\d+x\d+)", out))
    return (sizes.get("Override") or sizes["Physical"]).split("x")


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("tap", "swipe", "hold"):
        sys.exit(__doc__)
    w, h = screen_size()
    now = time.time()
    if args[0] == "tap" and len(args) == 3:
        x, y = args[1:]
        line, cmd = f"TOUCH_TAP {now:.3f} {x} {y} {w} {h}", ["tap", x, y]
    elif args[0] == "hold" and len(args) in (3, 4):
        x, y = args[1:3]
        ms = args[3] if len(args) == 4 else "800"
        line, cmd = f"TOUCH_TAP {now:.3f} {x} {y} {w} {h}", ["swipe", x, y, x, y, ms]
    elif args[0] == "swipe" and len(args) in (5, 6):
        x1, y1, x2, y2 = args[1:5]
        ms = args[5] if len(args) == 6 else "300"
        line, cmd = f"TOUCH_SWIPE {now:.3f} {x1} {y1} {x2} {y2} {w} {h}", ["swipe", x1, y1, x2, y2, ms]
    else:
        sys.exit(__doc__)
    print(line, flush=True)
    sys.exit(subprocess.run(adb() + ["shell", "input", *cmd]).returncode)


if __name__ == "__main__":
    main()
