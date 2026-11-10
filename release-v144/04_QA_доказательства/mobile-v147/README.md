# QA — Folio v147

- Web/PWA: added explicit focus ring for the keyboard-focusable import preview. Regression suite: 67/67.
- Android: APK 0.3.10 / versionCode 22 built, installed over 0.3.9 without clearing app data, then cold launched with Wi-Fi and mobile data disabled on AVD API 36. App opened offline; network settings restored after capture.
- Screenshot: `android-v147-offline.png`.
- APK SHA-256: `6a5911b7acb644e72d5950c3c156f7dd5ad8eccd4dbde68fca4e0c5f0dc3051e`.
- Windows WebView2 v147 onedir built. Native GUI launch for this exact build is not confirmed; v146 isolated GUI evidence is not attributed to v147.
- The full axe/import/replacement flow remains the v146 evidence; v147 only changes focus styling and has its own regression assertion.
