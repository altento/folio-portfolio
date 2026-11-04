# Android v93 cold offline launch

Debug APK SHA-256: `4ECF5DDB2A8B66F8285406E7C4825C4D07CACC07A7F2B9D14FDF30C6BED6DAEE`.

Installed on the isolated `FolioQA_API36` Android 36 AVD. Airplane-mode setting was `1` and Wi-Fi setting `0`; after force-stop the app relaunched into `ru.folio.portfolio/.MainActivity`. Chrome DevTools then forced the WebView network offline and reloaded the page. The v93 Service Worker controlled `https://localhost/` and served the Projects view with three cards. CSS viewport and document widths both measured 412 px, with no horizontal overflow.

Screenshots: settled offline launch and Projects view. Machine results: `results.json`. Reproduce WebView inspection with `verify-android-v93.mjs` after forwarding the current `webview_devtools_remote_<pid>` socket to port 9230.

This proves behavior on an emulator only. Physical-phone installation, accessibility services, and OEM file picker remain unverified.
