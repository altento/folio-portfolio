# Accessibility and runtime verification — v137

Date: 2026-11-05. Windows: packaged WebView2 executable, isolated profile. Browser viewports: 1440×1000 and touch-emulated 390×844. Android: emulator API 36.

## Windows WebView2 and browser accessibility

- The packaged EXE serves the app with HTTP 200 and returns 204 for the legacy SQLite migration seed when no old database exists.
- axe-core 4.14.0: 0 violations in the project editor at both viewports.
- All enabled visible form controls have accessible names.
- Keyboard Tab remained in the dialog over 22 transitions on desktop and phone. Escape closed it and restored focus to the exact opener, including the actual mobile bottom-navigation add button.
- The phone crop position changes independently from desktop and its preview remains visible.
- No browser console errors or uncaught page errors.
- `accessibility-v137-results.json` and `accessibility-editor-*.png` contain the packaged-runtime Playwright results and views; `windows-v137-runtime-results.json` records HTTP 200/204 and the untouched empty SQLite profile; `accessibility-v137.mjs` is the repeatable harness.

## Android runtime

APK 0.3.0 (versionCode 12, target SDK 36) installed over version 0.2.9 with `adb install -r`; Android did not uninstall the app or clear its data. The app launched, showed the normal service-worker update prompt, applied it using the in-app restart action, returned to the dashboard, and opened the three-step project editor. See `android-v137-runtime-results.json`, `android-v137-home.png`, and `android-v137-project-editor.png`.

Physical Android device, TalkBack/TTS, system magnification, and private-browsing behavior remain untested.
