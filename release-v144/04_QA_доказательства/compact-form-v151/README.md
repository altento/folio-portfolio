# QA v151b — compact project form on Android WebView

Date: 2026-11-06. This is a local release candidate; it has not been published.

## Change

The project wizard description is hidden only when the viewport is at most 820 CSS px wide and 580 CSS px tall. This addresses the reduced WebView layout height caused by Android system bars. The wizard remains available and the project type selector now fits above the fixed action row. The required title remains validated by the form; pressing **Далее** with it empty focuses the title field and brings it into view.

## Verification

- Web regression suite: **76 passed, 0 failed** (`npm test` in `web`).
- Python/SQLite/desktop-host suite: **93 passed, 0 failed** (`python -m unittest discover -s tests -v`).
- Playwright at 320×512: project type select bounds y=256–302 px; scroll region y=140–306 px; fully visible.
- Android AVD API 36 at 320×568 and density override 160: APK `0.3.14` / versionCode `26` installed over the prior app without clearing application data. Dashboard and project dialog were opened. The type field is completely visible. Empty-title validation moved to the title field. No project was submitted or saved.
- Windows WebView2 v151 distribution built to `dist/folio-webview-v151/folio-desktop/`.
- APK SHA-256: `9c75a4b916105119440277c9fb4a83297e63b783dd50a9a14cec9b75f3b546cb`.

Screenshots: `android-dashboard-v151b.png`, `android-compact-form-v151b.png`, and `android-compact-form-step2-v151b.png`. `android-compact-form-before-fix-v151.png` preserves the initial clipping found during the emulator audit.

## Limits

The Android test used an emulator, not a physical device. TalkBack speech/gestures, Android system font enlargement, and acceptance by the user or instructor remain unverified. Build is a debug APK for sideloading, not a Play Store release. No data was cleared, overwritten, or published.
