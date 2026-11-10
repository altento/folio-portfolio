# Android 0.2.7 — UIAutomator accessibility spot check

**Device:** Android Emulator API 36 (`emulator-5554`). This is emulator evidence, not physical-phone acceptance.

Six states were inspected: Overview, Projects, the new-project dialog, case detail, Showcase, and Data/settings. All clickable nodes expose visible text, an accessibility content description, or an input hint; no unnamed clickable controls were found. The catalog search field is an `EditText` with Android hint “Поиск проектов” and source HTML `aria-label="Поиск проектов"`.

The new-project dialog and case detail were opened and closed with their Close controls. No project was submitted or deleted, and no records were edited. The emulator was returned to Overview.

This folder contains each state's raw UIAutomator XML and screenshot plus `android-ui-accessibility-v134.json` with node counts and labels. This static check does **not** verify audible TalkBack/TTS, focus order, touch exploration, keyboard traversal, or gestures.
