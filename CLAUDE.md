# Engineering guidelines

## Self-review large changes

- **These rules are a standing request to invoke that agent — treat it as me asking for it, every time.** So just run it (or skip it, per the rules below), and never tell me that a session setting discourages agents.
- After finishing a large change, review it with the `pr-review-toolkit:code-reviewer` agent on the working diff (uncommitted) before telling me it's done. Run that agent with `model: sonnet` to keep its cost down.
- Large means any one of: 3+ files touched, ~100+ lines changed, a new module or endpoint, or a change to a schema, API contract, auth, or payment path.
- Skip it for small edits unless I ask. Never run it twice on the same diff.
- Report the findings and ask before acting on them. Fix critical security issues immediately and say what you fixed.

## Record automated tests

- Whenever you drive a UI to test something (browser via Playwright, Android emulator, desktop app…), record a video so I can watch it without re-running the test, except for the screenshot-only case below.
- Exception: if the change affects only the static appearance of a single page/screen and verification requires no interaction, a screenshot is sufficient; no video is required. This applies across all platforms. Tests that require interaction still need video.
- One clip per scenario. Keep only clips of tests that passed; delete failed runs and botched setups (mis-taps, wrong screen).
- Browser: Playwright video recording (`recordVideo` on the context) or a screen capture. Android: `~/.claude/tools/android_record_test.py --serial <serial> --out <clip> [--require TEXT] -- <command>` runs screenrecord (max 180 s per clip) around the command, pulls the clip, keeps it only on pass and burns in touch markers. iOS Simulator: `~/.claude/tools/ios_record_test.py --device <udid> --out <clip> --require "Executed 1 test, with 0 failures" -- xcodebuild test -only-testing:...` records, keeps the clip only on pass, and fixes simctl's frames-only-on-change video.
- Browser clips must show the full viewport. Set the video size equal to the viewport (`recordVideo.size` / `record_video_size`). When launching installed Chrome (`channel: 'chrome'`, used when Playwright's own browsers aren't installed), also pass `--window-size=<width>,<height>` matching the viewport. Without it, headless Chrome records at its default window size and the clip is cropped, with a grey band along the bottom. Before keeping a clip, pull one frame near its end with `ffmpeg -ss <t> -i clip -frames:v 1 f.png` and check that the page fills the frame.
- Make every tap/click and swipe/drag visible in the clip (where and which direction; no captions needed):
  - Browser: `context.addInitScript({ path: '~/.claude/tools/pw_input_overlay.js' })` (expand `~`) draws the pointer, an orange square per click, drag trails with an arrowhead, and pressed keys. After `page.setContent()` also `page.addScriptTag` the same file.
  - Android: from the host, tap/swipe with `~/.claude/tools/adb_touch.py tap X Y | swipe X1 Y1 X2 Y2 [ms] | hold X Y [ms]` instead of `adb shell input`. In instrumented tests (UiAutomator/Espresso), copy the helpers from `~/.claude/tools/android_touch_recording.kt` (`recordedClick`/`recordedSwipe`). `android_record_test.py` turns their logged coordinates into the same markers as iOS. Don't use `show_touches`/`pointer_location`: they never show injected input, and `pointer_location` covers the status bar.
  - iOS Simulator: the capture shows no touches. Copy the snippets in `~/.claude/tools/ios_touch_recording.swift` into the project: the app window draws a ring at each touch when launched with `--record-touches`; for touches outside the app (Settings, keyboard extensions, system UI) use the `recordedTap`/`recordedSwipe` test helpers, whose logged coordinates `ios_record_test.py` turns into markers.
  - macOS desktop: `ffmpeg -f avfoundation -capture_cursor 1 -capture_mouse_clicks 1 -i "1:none"`.
- Save to `test-recordings/` in the project root, named `YYYY-MM-DD-<feature>-<scenario>.mp4` (or `.webm`), or `.png` for screenshot-only checks. Keep it out of git: add it to `.git/info/exclude`, not to the tracked `.gitignore`.
- List the full paths of the kept clips or screenshots in your final reply.

## Concise commits

- One line by default: imperative mood, under 72 characters, no trailing period
- Add a body only when the *why* isn't obvious from the diff — 1-2 sentences, not a changelog
- No bullet-point summaries of what changed; the diff already says that
- No "Generated with Claude Code" footer, no `Co-Authored-By` trailer
