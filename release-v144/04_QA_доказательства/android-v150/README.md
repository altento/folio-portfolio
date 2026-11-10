# Android v150 — offline smoke and backup settings

Date: 06.11.2026. Android Emulator API 36, Android 0.3.13 / versionCode 25, Web/PWA v150.

## Runtime

The APK was installed with `adb install -r`, preserving the emulator app data. The app was force-stopped and launched again with airplane mode enabled and `Active default network: none`. The dashboard rendered with three demo projects. The settings route rendered on the emulator phone viewport, including the JSON transfer instructions and the state **«Резервная копия не отмечена»**. The JSON export button was not activated; no file was written to Downloads. Runtime logs had no AndroidRuntime, Chromium or Capacitor error lines in the inspected window.

Screenshots: `android-v150-offline.png` and `android-v150-settings-backup-offline.png`. The second image shows the settings card and the unmarked-backup message.

## Accessibility snapshot

TalkBack was enabled temporarily to collect `android-v150-settings-talkback-uia.xml`; it was turned off afterward and the original accessibility setting was restored (`enabled_accessibility_services=null`, `accessibility_enabled=0`). The settings tree contained 23 clickable controls and 0 clickable controls without a name, hint or content description. Input hints supply names for several optional text fields. An unnamed focusable `main-content` landmark with `tabindex=-1` is programmatically focusable but not a clickable action. This UI tree check does not verify spoken output or gesture navigation.

## Scope and restoration

No application data was cleared. At the end, airplane mode was off, Wi-Fi and mobile-data toggles were enabled, and TalkBack was disabled. The emulator had no active default network after restoration. No public deployment or upload occurred. Physical Android hardware, TalkBack audio/gesture walkthrough and system zoom remain unverified.
