# QA mobile case form, accessibility and import safety v109

Date: 2026-11-02. Product snapshot: desktop Tk/SQLite v91; responsive web/PWA and Android WebView v109.

## What changed

The long case editor remains one form and becomes a three-step flow on phones; desktop keeps the complete form visible. This release also fixes three axe findings in the phone form: the empty tags message is a valid list item, tag entry has a visible associated label, and the progress panel is an accessible group rather than a duplicate landmark.
The v109 refinement makes each gallery caption the single accessible description for its image, avoiding duplicate screen-reader announcements.

## Browser coverage

- `wizard-e2e-v106.mjs`: Chromium 390x844; required-field validation, all three steps, previous/next, hidden values preserved, create/edit survive reload, no uncaught errors or horizontal overflow.
- `keyboard-focus-v109.mjs`: visible heading focus, Tab remains in the dialog, and focus is restored to the visible step heading when a field is hidden by the mobile breakpoint. Result: `keyboard-focus-v109-results.json`; focus screenshot: `keyboard-step-2-focus-v109.png`.
- Import hardening v108: strict schema/next-ID/title validation, at most 130,000 projects, 250 images, 24 million image-data characters, and 120 million aggregate decoded pixels. These bounds are covered by web regression tests.
- `responsive-qa.mjs`: 320x568 phone and 1440x900 desktop; no horizontal overflow. The mobile Next action remains visible in the sticky dialog footer after scrolling; desktop keeps the full form and regular Save.
- `dashboard-visual-qa.mjs`: 1440x1000 desktop and 390x844 phone; hero illustration and all three covers decode successfully, no page errors or horizontal overflow.
- `a11y-audit-v109.mjs` uses the included axe-core 4.14.0 runtime and scans dashboard, mobile form steps 1–3, and desktop form. Result: 5 states, 0 violations. It also records labels, focus target, and progress state. Three rules remain axe `incomplete` and need human judgment.

Run the browser scripts while a static server serves `web/` at `http://127.0.0.1:8771/`; they use bundled Playwright and installed Chrome paths from the task environment.

## Android evidence

`android-v109-offline.png` records a clean cold launch on Android Emulator API 36 with Wi-Fi disabled and network stats reporting no connected network. `android-v109-form.png` shows the three-step form in the Capacitor wrapper. The v109 APK signature (v2), zip alignment, phone ZIP CRC and APK hash are verified. No physical phone or TalkBack test was performed.

## Regression and report gate

- Web: 44/44; Python/SQLite: 62/62.
- `node --check app.js`, `core.js`, `sw.js`: PASS.
- M4/M5 current PDFs were exported from read-only temporary DOCX copies and all 21 pages were rendered and visually inspected. Source and package PDF copies are reconciled by the current submission package verifier.
- Android debug APK v109 SHA-256: `c0e5cf78e58d0bd9112236e215dbce48157ee9d90500cbc4d3e8f558ad7bbce9`. Not a store release.

## Screenshot inventory

- `android-v106-form.png` — 294734 bytes, SHA-256 `aa7607973d7d6c7386cbd2dd5fce8fdc98a26a800ee5be003f16f4c4ac288ece`
- `android-v106-offline.png` — 980785 bytes, SHA-256 `ff11194e5b4e8923afc5af06b517ea5f67e6c63983a165253aa2c308b08db07e`
- `dashboard-desktop-v106.png` — 658912 bytes, SHA-256 `7412355403b6b61ae824bd68ff69b3174b94c38ac5f66196708a28ce629b8d0f`
- `dashboard-mobile-v106.png` — 158970 bytes, SHA-256 `a7f4c12db45ca7bd877e4c653fcd0c44f9273b260b265c2a530f3f8f6c7580d2`
- `desktop-form.png` — 224945 bytes, SHA-256 `da3b6dd3ab987eca0d2239ba4b39e58b594e88e80349adfc532952d18edd1324`
- `mobile-320-basics-actions.png` — 17053 bytes, SHA-256 `0e079ce16f2ee65e148b0de202f87e9017251d2b593937811449f05b2d5e8e89`
- `mobile-320-basics.png` — 30528 bytes, SHA-256 `8f2099fe253013e10616dd8291d0ebf75aa948ba2e28f85d76617dda1a6f0bbd`
- `step-1-basics.png` — 40318 bytes, SHA-256 `e3591b782005975fd46d20faddaf0ba6349819f9a5d257faf55438d63b99af1e`
- `step-2-story.png` — 43790 bytes, SHA-256 `443506c9d47b72f5fb826f3ef234f778b947d55fe9f8ac806c14e19d3c98a9bc`
- `step-3-media.png` — 71542 bytes, SHA-256 `9d6320b56592a1119cd694c10f5ff34a8e256db5254e12d5c3faccd1710ebb50`

## Submission package v109

The v109 package contains 1,792 payload files plus its manifest (1,793 files in the ZIP). Package-level Python/SQLite regression passed 62/62 and web regression passed 44/44; manifest hashes and ZIP CRC pass, current source reports/PDFs and Android APK match packaged copies, and personal project databases are excluded. The exact archive SHA-256 is stored in the adjacent `.sha256` sidecar.

- `android-v108-form.png` — 297131 bytes, SHA-256 `7dceeb5e3260063f5c52a76508c7756ee3abd18579cd1b997b0234265bdd8f2d`.

- `android-v108-offline.png` — 981342 bytes, SHA-256 `30e1869b6606ff7c83984fbd77477a0c19f741fbc89d8a9e6971652129f80638`.

- `keyboard-step-2-focus-v108.png` — 44282 bytes, SHA-256 `71cb92320ea24a768f8a6ff52975bf3f67317c6fe8cb872a938f3c755a1b9583`.
