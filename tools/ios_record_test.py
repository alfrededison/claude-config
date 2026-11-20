#!/usr/bin/env python3
"""Record an iOS Simulator test run; keep the clip only if it passes; burn in touch markers.

    ios_record_test.py --device UDID --out CLIP.mp4 [--require TEXT ...] -- COMMAND...

Starts `simctl io recordVideo`, waits for "Recording started", runs COMMAND (e.g. `xcodebuild
test -only-testing:...`) with its output in CLIP.log, then stops the recording. The clip is
deleted unless COMMAND exits 0 and every --require string appears in its output (e.g.
--require "Executed 1 test, with 0 failures" to make sure the filter matched exactly one test).

Touch markers come from TOUCH_TAP / TOUCH_SWIPE lines the test prints before each action (see
ios_touch_recording.swift); touch_markers.py documents the format and burns them in.
"""
import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import touch_markers  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--device", required=True, help="Simulator UDID (or 'booted')")
    p.add_argument("--out", required=True, type=Path, help="clip path, e.g. test-recordings/2026-11-08-x-y.mp4")
    p.add_argument("--require", action="append", default=[], help="text that must appear in the output")
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        p.error("missing COMMAND after --")
    clip = a.out.resolve()
    if clip.exists():
        sys.exit(f"refusing to overwrite {clip}")
    clip.parent.mkdir(parents=True, exist_ok=True)
    log_path, rec_log = clip.with_suffix(".log"), clip.with_suffix(".recorder.log")

    passed = False
    with rec_log.open("w") as rl:
        rec = subprocess.Popen(["xcrun", "simctl", "io", a.device, "recordVideo", "--codec=h264", "--force", str(clip)],
                               stdout=rl, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 20
        while "Recording started" not in rec_log.read_text():
            if rec.poll() is not None or time.monotonic() > deadline:
                raise SystemExit(f"recording did not start: {rec_log.read_text()}")
            time.sleep(0.2)
        started = time.time()
        with log_path.open("w") as log:
            r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=a.timeout)
        out = log_path.read_text()
        missing = [s for s in a.require if s not in out]
        passed = r.returncode == 0 and not missing
        if missing:
            print(f"missing in output: {missing}", file=sys.stderr)
    finally:
        ended = time.time()
        if rec.poll() is None:
            rec.send_signal(signal.SIGINT)
        try:
            if rec.wait(timeout=20) != 0:
                passed = False
        except subprocess.TimeoutExpired:
            rec.kill(); rec.wait(); passed = False
        rec_log.unlink(missing_ok=True)
        if not passed:
            clip.unlink(missing_ok=True)
    if not passed:
        sys.exit(f"FAIL: clip deleted. Output: {log_path}")
    try:
        touch_markers.burn(clip, *touch_markers.parse(log_path.read_text()), started, ended - started)
    except BaseException:
        clip.unlink(missing_ok=True)
        raise
    log_path.unlink()  # only failures need the output
    print(f"PASS {clip}")


if __name__ == "__main__":
    main()
