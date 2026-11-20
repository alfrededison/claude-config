# claude-config

My global Claude Code setup: the rules in `CLAUDE.md` and the helper scripts they point to in `tools/`.

## Install

```sh
./install.sh
```

This symlinks `~/.claude/CLAUDE.md` and `~/.claude/tools` to this repo, so edits made either way end up here. If either path already exists, it is moved aside to `<name>.bak-<timestamp>` first.

## Tools

Recording UI tests with every tap and swipe visible:

| File | What it does |
| --- | --- |
| `ios_record_test.py` | Records an iOS Simulator test run, keeps the clip only if the test passes, and burns in touch markers. |
| `ios_touch_recording.swift` | Snippets to copy into an iOS project: a touch ring drawn inside the app, plus test helpers that log touches. |
| `android_record_test.py` | Records an Android run with `screenrecord`, keeps the clip only if the test passes, and burns in touch markers. |
| `adb_touch.py` | `tap` / `swipe` / `hold` through adb, logging each action so it gets a marker. |
| `android_touch_recording.kt` | Snippets to copy into UiAutomator/Espresso tests so they log their touches. |
| `touch_markers.py` | Shared code: parses `TOUCH_TAP` / `TOUCH_SWIPE` lines and draws the markers with ffmpeg. |
| `pw_input_overlay.js` | Playwright init script that draws the pointer, clicks, drags and pressed keys into recorded videos. |
| `caption_video.py` | Burns timed text captions into any recording. |

Requirements: Python 3 and ffmpeg. `adb` for Android, Xcode for iOS, Playwright for web, and Pillow for `caption_video.py`.
