# Android v152 smoke — AVD API 36

Date: 2026-11-07. The debug APK 0.3.15 (versionCode 27, target SDK 36) was installed over 0.3.14/code 26 on `FolioQA_API36` using `adb install -r`. `firstInstallTime` remained unchanged; app data was not cleared.

After installation, the app opened on the dashboard and project catalog. Searching `CRM` showed one case. Reset cleared the query and restored the three demo cases. A cold force-stop/start while Wi-Fi and mobile data were disabled loaded the dashboard offline. Network was restored after the check. No create, edit, import, export, or delete operation was performed. This is an emulator smoke, not a physical-phone or TalkBack audio/gesture test.

APK SHA-256: `5302cda38bafc804726a988182e6b1a3c8dcdc1b6e40971b2ca99364cf5cd493`.

Screenshots and machine-readable checksums: `android-v152-catalog.png`, `android-v152-search.png`, `android-v152-reset.png`, `android-v152-offline.png`, `result.json`.
