# Android v102 cold offline smoke

Source APK: `mobile/folio-android-debug.apk`.

The build was installed over the existing API 36 emulator app, then the emulator test app data was cleared with `pm clear`. Wi-Fi and mobile data were disabled, the app was force-stopped, and the package was relaunched. The package is installed and foreground activity belongs to `ru.folio.portfolio`; the PNG screenshot signature is valid.

- Result: PASS
- API: 36 (`emulator-5554`)
- APK SHA-256: `d563efc0c6d7476ee8a1fced524fea6a5d856c58446d645e7edbd75ef3fb56ae`
- APK signature: v2 PASS
- `zipalign -c -v 4`: PASS
- Screenshot: `android-v102-cold-offline-home.png`

This verifies an Android Emulator cold offline launch, not a physical phone, OEM file picker, screen reader or release-signed build.
