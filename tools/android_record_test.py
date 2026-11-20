#!/usr/bin/env python3
"""Record an Android test run; keep the clip only if it passes; burn in touch markers.

    android_record_test.py --serial emulator-5554 --out CLIP.mp4 [--require TEXT ...] -- COMMAND...

Starts `adb shell screenrecord`, waits until it is capturing, runs COMMAND (a shell script of
adb_touch.py calls, `./gradlew connectedAndroidTest`, `adb shell am instrument ...`) with its
output in CLIP.log, then stops the recording and pulls it. The clip is deleted unless COMMAND
exits 0 and every --require string appears in its output. COMMAND runs with ANDROID_SERIAL set.

Touch markers come from TOUCH_TAP / TOUCH_SWIPE lines (format in touch_markers.py), read from
COMMAND's output and from logcat tag TOUCH. Print them with:
  - adb_touch.py tap/swipe/hold, for tests driven from the host (instead of `adb shell input`);
  - the helpers in android_touch_recording.kt, for instrumented tests (UiAutomator/Espresso).
Android's own show_touches / pointer_location never show injected input (adb input, UiAutomator,
Espresso), so these markers are the only way such touches appear in the clip.

screenrecord stops by itself after 180 s; a longer run fails, so split the scenario.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import touch_markers  # noqa: E402

LIMIT = 180


def clock_offset(adb):
    """Device epoch minus host epoch, from the fastest of a few round trips."""
    best = None
    for _ in range(3):
        t0 = time.time()
        dev = float(subprocess.check_output(adb + ["shell", "date", "+%s.%N"], text=True).strip())
        t1 = time.time()
        if best is None or t1 - t0 < best[0]:
            best = (t1 - t0, dev - (t0 + t1) / 2)
    return best[1]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--serial", default=os.environ.get("ANDROID_SERIAL"), help="adb serial (default $ANDROID_SERIAL)")
    p.add_argument("--out", required=True, type=Path, help="clip path, e.g. test-recordings/2026-11-20-x-y.mp4")
    p.add_argument("--require", action="append", default=[], help="text that must appear in the output")
    p.add_argument("--bit-rate", default="8M")
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        p.error("missing COMMAND after --")
    if not a.serial:
        p.error("--serial (or $ANDROID_SERIAL) is required")
    adb = ["adb", "-s", a.serial]
    clip = a.out.resolve()
    if clip.exists():
        sys.exit(f"refusing to overwrite {clip}")
    clip.parent.mkdir(parents=True, exist_ok=True)
    log_path, rec_log, touch_log = (clip.with_suffix(s) for s in (".log", ".recorder.log", ".touch.log"))
    remote = f"/sdcard/rec-{os.getpid()}-{int(time.time())}.mp4"
    offset = clock_offset(adb)

    passed = False
    started = ended = time.time()
    with rec_log.open("w") as rl:
        rec = subprocess.Popen(adb + ["shell", "screenrecord", "--verbose", "--bit-rate", a.bit_rate,
                                      "--time-limit", str(LIMIT), remote], stdout=rl, stderr=subprocess.STDOUT)
    with touch_log.open("w") as tl:
        # -T 1: start from the newest line instead of dumping the whole buffer; older lines are
        # dropped below by timestamp.
        cat = subprocess.Popen(adb + ["logcat", "-v", "raw", "-s", "TOUCH:I", "-T", "1"],
                               stdout=tl, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 20
        while "Content area" not in rec_log.read_text():
            if rec.poll() is not None or time.monotonic() > deadline:
                raise SystemExit(f"recording did not start: {rec_log.read_text()}")
            time.sleep(0.1)
        started = time.time()
        with log_path.open("w") as log:
            try:
                r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=LIMIT - 3,
                                   env={**os.environ, "ANDROID_SERIAL": a.serial})
                rc = r.returncode
            except subprocess.TimeoutExpired:
                print(f"COMMAND ran past {LIMIT - 3} s, the screenrecord limit; split the scenario", file=sys.stderr)
                rc = -1
        out = log_path.read_text()
        missing = [s for s in a.require if s not in out]
        passed = rc == 0 and not missing
        if missing:
            print(f"missing in output: {missing}", file=sys.stderr)
    finally:
        ended = time.time()
        subprocess.run(adb + ["shell", "pkill", "-INT", "screenrecord"], capture_output=True)
        try:
            rec.wait(timeout=20)
        except subprocess.TimeoutExpired:
            rec.kill(); rec.wait(); passed = False
        if "Encoder stopping" not in rec_log.read_text():
            print(f"recorder did not stop cleanly: {rec_log.read_text()}", file=sys.stderr)
            passed = False
        cat.terminate(); cat.wait()
        if passed:
            time.sleep(0.5)  # let the muxer finish the file
            if subprocess.run(adb + ["pull", remote, str(clip)], capture_output=True).returncode != 0:
                print("adb pull failed", file=sys.stderr)
                passed = False
        subprocess.run(adb + ["shell", "rm", "-f", remote], capture_output=True)
        rec_log.unlink(missing_ok=True)
        if not passed:
            clip.unlink(missing_ok=True)
            touch_log.unlink(missing_ok=True)
    if not passed:
        sys.exit(f"FAIL: clip deleted. Output: {log_path}")
    try:
        taps, swipes = touch_markers.parse(log_path.read_text())
        dt, ds = touch_markers.parse(touch_log.read_text(), clock_offset=offset)
        taps += [e for e in dt if e[0] >= started - 1]
        swipes += [e for e in ds if e[0] >= started - 1]
        touch_markers.burn(clip, taps, swipes, started, ended - started)
    except BaseException:
        clip.unlink(missing_ok=True)
        raise
    finally:
        touch_log.unlink(missing_ok=True)
    log_path.unlink()  # only failures need the output
    print(f"PASS {clip} ({len(taps)} taps, {len(swipes)} swipes marked)")


if __name__ == "__main__":
    main()
