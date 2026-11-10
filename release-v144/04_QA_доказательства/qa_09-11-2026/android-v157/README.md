# Android v157 candidate update check

Date: 9 November 2026. Package `ru.folio.portfolio` version 0.3.20, versionCode 32, was installed with `adb install -r` onto the Android API 36 AVD over version 0.3.19. The app was not uninstalled and its app data was not cleared.

`first-launch.png` shows the available-update notice. After selecting “Перезапустить”, `after-update.png` shows the notice cleared and the dashboard restored with demo content. The post-update UIAutomator XML contains 107 nodes, 18 named clickable elements and 0 unnamed clickable elements. Package metadata confirms version 0.3.20/code 32.

This is emulator evidence only. Physical-phone behavior, TalkBack speech and gestures, and OEM file selection were not tested.

- Machine-readable protocol: `result.json`
- First-launch hierarchy: `window.xml`
- Post-update hierarchy: `window-after-update.xml`
