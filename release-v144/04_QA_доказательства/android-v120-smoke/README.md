# Android v120 smoke

Debug APK v120 was installed over the previous QA app on Android API 36 with `adb install -r`, preserving app data. The old Service Worker correctly offered a restart after installation; after applying it the banner disappeared and v120 assets appeared. Screenshot and protocol are included. This verifies update/launch only, not physical-device or TalkBack/TTS acceptance.
