# folio для Android

Текущий Android debug APK — 0.3.24 (versionCode 36) со встроенными Web/PWA ресурсами v161. Он установлен через `adb install -r` поверх 0.3.22 на выделенный AVD API 36 без очистки данных; баннер обновления и холодный офлайн-запуск зафиксированы. Снимки и протокол: `../../04_QA_доказательства/qa_10-11-2026/android-v161/`. UIAutomator увидел только контейнер WebView; внутреннее дерево WebView, физический телефон и речь/жесты TalkBack этим прогоном не подтверждены. APK подписан debug-ключом, это не сборка Google Play.

SHA-256 APK: `4e658f6abdfd5ec8dfd47865597c02996a03ce23cc84452f7a35183564cf8cb7`.

### Пересборка на Windows

Нужны Node.js, Java 21 и Android SDK Platform 36, Build-Tools 36.0.0, Platform-Tools. Из корня проекта запустите `powershell -ExecutionPolicy Bypass -File .\mobile\build-android.ps1`. Скрипт собирает web-ассеты и debug APK, после чего обновляет файл APK и ZIP-архив для телефона. Принятие SDK-лицензий должно быть выполнено заранее через SDK Manager.

### Историческая сборка — Android 0.3.9 / web/PWA v146 доступность импорта (05.11.2026)

В диалоге импорта прокручиваемая область получила имя и фокус с клавиатуры; кнопка «Отмена» находится в заголовке, действия разделены безопасным расстоянием. Axe-core 4.14.0 обнаружил 0 нарушений на 320×568 и 390×568 px; Shift+Tab/Escape и возврат фокуса проверены. Сценарий add/replace проверил загрузку pre-replace backup и сохранение одной synthetic записи. Web regression — 66/66; Python/SQLite — 91/91. Android APK 0.3.9/code 21 собран, установлен поверх 0.3.8 без очистки данных и холодно запущен офлайн на AVD API 36; данные остаются локальными.

SHA-256 APK: `d995c9e4f69ad4c1aa8abb81062dcadf275c0c59b4618f58df3c8259a5e81e08`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v148 High Contrast и безопасная замена (06.11.2026)

Web/PWA v148 adds Windows forced-colors system palette and waits for a saved pre-replace backup; Web regression is 69/69. Android 0.3.11 debug APK is built but not yet installed on an emulator in this QA pass. Storage stays local.

SHA-256 APK: `cba9a9aa2a8ab838d1e3aaab310eb53587d07b49469331b761389d78c3055b3e`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v149 mobile closed-dialog (06.11.2026)

Web/PWA v149 hides a closed import dialog at mobile widths; Web regression is 70/70. Android debug 0.3.12 / code 24. Runtime on a physical phone or AVD is still unverified; storage stays local.

SHA-256 APK: `1e7b160dd69a6f169602e979d0fd52737bf14c004bbec949613833184ddc77b5`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v152 mobile toolbar readability (07.11.2026)

Web/PWA v152 improves mobile catalog toolbar readability; Android debug 0.3.15 / code 27. The APK is rebuilt from v152 web assets and installed over existing AVD data without clearing it. Physical-phone TalkBack audio/gestures remain unverified.

SHA-256 APK: `5302cda38bafc804726a988182e6b1a3c8dcdc1b6e40971b2ca99364cf5cd493`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v153 доступность уведомления обновления (08.11.2026)

Web/PWA v153 separates the update announcement from its action controls; Axe-core 4.14.0 reports 0 violations for the visible notice at 390×844 and 1440×900, and the dismiss action hides it. Android debug 0.3.16 / code 28 is rebuilt from v153 web assets and installed over existing AVD data without clearing it. Physical-phone TalkBack audio/gestures remain unverified.

SHA-256 APK: `e68a4d66630e68b616a12cd58d030d07d130c0d00e36b78d7a159d4636751190`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v159 читаемость мобильных меток (10.11.2026)

Web/PWA v159 raises small mobile dashboard labels, recommendation badges, statistic captions and project tags to 10–11 px while preserving layout at 320 px. Android debug 0.3.22 / code 34 is built from the same web assets and installed over 0.3.21 on the dedicated AVD without clearing app data. The update notice, launch and offline behavior are documented with screenshots and protocol in `../../04_QA_доказательства/qa_10-11-2026/android-v159/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.

SHA-256 APK: `fa60dd29102c02a2e7735481d9eb12f5f0c885dd4e853df70ccf06887934344d`. Это debug APK, не для магазина.

### Текущая сборка — Web/PWA v161 accessible vector controls and contrast (10.11.2026)

Web/PWA v161 makes decorative symbols inside icon-only controls silent to screen readers and adds stable high-contrast backing for labels over artwork, including bright custom covers. Android debug 0.3.24 / code 36 is built from the same web assets and installed over 0.3.23 on the dedicated AVD without clearing app data. The update notice, launch and offline behavior are documented with screenshots and protocol in `../../04_QA_доказательства/qa_10-11-2026/android-v161/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.

SHA-256 APK: `4e658f6abdfd5ec8dfd47865597c02996a03ce23cc84452f7a35183564cf8cb7`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v160 доступность раскрытия мобильных фильтров (10.11.2026)

Web/PWA v160 fixes the mobile filter and saved-view disclosures: closed controls are removed from layout and accessibility navigation until their section is opened. Android debug 0.3.23 / code 35 is built from the same web assets and installed over 0.3.22 on the dedicated AVD without clearing app data. The update notice, launch and offline behavior are documented with screenshots and protocol in `../../04_QA_доказательства/qa_10-11-2026/android-v160/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.

SHA-256 APK: `545305cc56c54f5fb503922ea974b5c9cb7e34fdfc66a86713cb1c1afd39268e`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v158 исправление счётчика подсказок (10.11.2026)

Web/PWA v158 fixes the duplicated Russian recommendation count in the dashboard badge; the PWA and Android share these web assets. Android debug 0.3.21 / code 33 is installed over 0.3.20 on the dedicated AVD without clearing app data. The update notice, launch and offline behavior are documented with screenshots and protocol in `../../04_QA_доказательства/qa_10-11-2026/android-v158/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.

SHA-256 APK: `5b8c36bebf2bbb6a92b814203af128250d8cb02455d3be975fe1b2f361aa08dc`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v157 локальная копия восстановления (09.11.2026)

Web/PWA v157 keeps the PWA and Android interface aligned and adds a Windows-only local recovery copy outside WebView storage. Android debug 0.3.20 / code 32 is built from v157 assets and installed over 0.3.19 on the dedicated AVD without clearing data. The update notice and cold offline restart are documented with current screenshots and protocol in `../../04_QA_доказательства/qa_09-11-2026/android-v157/`. UIAutomator reports only the WebView container, so no inner-control label counts are claimed. Physical-phone file picker and TalkBack audio/gestures remain unverified.

SHA-256 APK: `e08abcbe9947b46ea2da44f9fbfb1b1da3335b7db7577247dfc50cddd87fc9ff`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v156 единое объяснение локального хранения (09.11.2026)

Web/PWA v156 explains the same local-data boundary across browser, Windows and Android: portfolio data stays in the current app profile and does not sync automatically. The settings page also clarifies what a data reset removes and why JSON backups should be stored privately. Android debug 0.3.19 / code 31 is built from v156 assets and installed over the prior AVD state without clearing data; the update notice appeared, the new cache applied after restart, and the dashboard opened. The resulting UIAutomator XML contains 107 nodes, 18 named clickable controls and 0 unnamed clickable controls. Current AVD screenshots and protocol: `../../04_QA_доказательства/qa_09-11-2026/android-v156/`. Physical-phone TalkBack audio/gestures remain unverified.

SHA-256 APK: `264ecb00d0fc17bc9eaf3c2e56cb45b10760370138b5deaa13218c00c5e7fa52`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v155 приватность резервной копии (09.11.2026)

Web/PWA v155 makes the local-data boundary explicit: JSON backup contains the complete profile, including contacts hidden from the showcase, and Folio does not add its own at-rest encryption. Store backups privately and rely on device/account protections. Android debug 0.3.18 / code 30 is built from v155 assets; physical-phone TalkBack audio/gestures remain unverified.

SHA-256 APK: `30ae0763aec60aabb26143d296141c17cd6ae857d35e28ce1a5dc965bc0b1047`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v154 мобильные зоны нажатия (08.11.2026)

Web/PWA v154 keeps the catalog's primary action at 44 CSS px on compact phones. Responsive route QA measures the full clickable label around native checkboxes, so the visible square no longer produces a false small-target warning. Android debug 0.3.17 / code 29 is rebuilt from v154 web assets and installed over existing AVD data without clearing it. Physical-phone TalkBack audio/gestures remain unverified.

SHA-256 APK: `dce9acee471bf8bab3f8a116d03964a2b01520526931e7c72f01e70508b2770d`. Это debug APK, не для магазина.


### Историческая сборка — Web/PWA v151 compact short-screen form (06.11.2026)

Historical v151 first compact-form pass. Android AVD audit later found the form clipped after Android system bars reduced the WebView layout viewport; the follow-up fix and retest are recorded in v151b below.

SHA-256 APK: `9c75a4b916105119440277c9fb4a83297e63b783dd50a9a14cec9b75f3b546cb`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v151b Android compact viewport (06.11.2026)

Web/PWA v151b compacts the project wizard on Android WebView short viewports. Android debug 0.3.14 / code 26. Installed over existing AVD data without clearing it; opened the dashboard and project form at 320×568 and confirmed the type selector is visible. Playwright verified the 320×512 CSS viewport. Physical-device TalkBack audio/gestures remain unverified.

SHA-256 APK: `9c75a4b916105119440277c9fb4a83297e63b783dd50a9a14cec9b75f3b546cb`. Это debug APK, не для магазина.

### Историческая сборка — Web/PWA v150 backup status (06.11.2026)

Web/PWA v150 shows a truthful local JSON-backup status; Web regression is 75/75. Android debug 0.3.13 / code 25. AVD API 36: install over existing data, cold offline launch and Settings backup status verified. TalkBack UIA shows 23 named clickable controls in Settings; audio/gestures and physical-device runtime remain unverified. Storage stays local.

QA: `служебные_файлы/qa_06-11-2026/android-v150/`. SHA-256 APK: `b3d2dbc1bbaf121a69d0994d5622a20c176c7e08f149b946b6c07143b8ac3655`. Это debug APK, не для магазина.


### Историческая сборка — web/PWA v147 focus ring предпросмотра импорта (05.11.2026)

Web/PWA v147 adds a visible focus ring to the import preview; regression is 67/67. Dialog structure, axe-core 0 violations at 320/390 px, keyboard Escape/focus return, and JSON add/replace were verified on v146. Android APK 0.3.10 (versionCode 22) is a debug build installed without clearing user data and cold-started offline on AVD API 36; storage remains local.

SHA-256 APK: `6a5911b7acb644e72d5950c3c156f7dd5ad8eccd4dbde68fca4e0c5f0dc3051e`. Это debug APK, не для магазина.

### Историческая сборка — Android 0.3.8 / web/PWA v145 mobile import actions (05.11.2026)

Web/PWA v145 улучшает мобильный диалог JSON-импорта: пояснения прокручиваются отдельно, панель действий всегда остаётся доступной; проверены размеры 320/390 px. Возможности v144 (сортировка по полному набору тегов и сохранённые виды) сохранены. Web regression — 66/66; Python/SQLite — 91/91. Android APK 0.3.8 (versionCode 20) собран для проверки; пользовательские данные не очищаются при обновлении, данные остаются локальными.

SHA-256 APK: `07779e88912865b95ec69a6e81bcd1f902e99392fb56526d8de298154693bed7`. Это debug APK, не для магазина.


### Историческая сборка — Android 0.3.7 / web/PWA v144 tag sorting (05.11.2026)

Web/PWA v144 добавляет сортировку по полному набору тегов в общем интерфейсе Web, PWA, Windows WebView2 и Android. Сравнение игнорирует регистр; нетегированные кейсы помещаются в конце. Сохранённые фильтры продолжают восстанавливать выбранный вариант сортировки. Web regression — 66/66; Python/SQLite — 91/91. Android APK 0.3.7 (versionCode 19) собран для проверки; пользовательские данные не очищаются при обновлении, данные остаются локальными.

SHA-256 APK: `14152f66ff1ae86e970b42fffdc4ff58e55e8e5bf2dc82df7eb521b0ccd52d79`. Это debug APK, не для магазина.


### Историческая сборка — web/PWA v137 mobile dialog focus return (05.11.2026)

Web/PWA v137 сохраняет и применяет независимое положение обложки для компьютера и телефона. После открытия редактора мобильной кнопкой нижней навигации клавиатурный фокус после Escape возвращается к исходной кнопке. axe-core 4.14.0: 0 нарушений в редакторе при 1440×1000 и 390×844; проверены 22 перехода Tab, удержание фокуса внутри диалога и возврат фокуса на мобильную кнопку. Python/SQLite 91/91, Web 63/63. APK 0.3.0 (versionCode 12) установлен поверх 0.2.9 на AVD API 36 без очистки данных, открыт и проверен; после уведомления Service Worker штатная перезагрузка успешно применила обновление.

SHA-256 APK: `bdb428d9a4027599889be5739b9701fc9465d457c6dff218299f35e0dfe88f37`. Это debug APK, не для магазина.

### Историческая сборка — web/PWA v136 responsive cover crop preview (05.11.2026)

Web/PWA v136 добавляет отдельное кадрирование обложки для компьютера и телефона в редакторе проекта и адаптивном HTML-экспорте. На телефоне предпросмотр обложки расположен рядом с ползунками. Телефонный кадр необязательный, наследуется от компьютерного, проходит валидацию и переносится в JSON/SQLite. Совместимость старых портфолио сохранена. Проверены создание, переключение режимов и независимость кадров на 1440×1000 и 390×844, а также Android WebView на AVD API 36; Python/SQLite 91/91, Web 63/63. APK 0.2.9 (versionCode 11) установлен поверх 0.2.8 без очистки данных и запущен. Физический телефон, аудио TalkBack/TTS, системное увеличение и private-mode поведение остаются открытыми.

SHA-256 APK: `04ae5c4440d262a89f29a772b887511a1994ce13ca83f42b54e7d0f66d28d3dc`. Это debug APK, не для магазина.


### Историческая сборка — web/PWA v135 responsive per-device cover crop (05.11.2026)

Web/PWA v135 добавляет отдельное кадрирование обложки для компьютера и телефона в редакторе проекта и адаптивном HTML-экспорте. Телефонный кадр необязательный, наследуется от компьютерного, проходит валидацию и переносится в JSON/SQLite. Совместимость старых портфолио сохранена. Проверены создание, переключение режимов и независимость кадров на 1440×1000 и 390×844; Python/SQLite 91/91, Web 63/63. Android APK 0.2.8 (versionCode 10) установлен поверх 0.2.7 на AVD API 36 без очистки данных и запущен. Физический телефон, аудио TalkBack/TTS, системное увеличение и private-mode поведение остаются открытыми.

SHA-256 APK: `6b80f4628859b31ae2328eba428a173eeea275f45e6857a676d096d5ae8f3ff3`. Это debug APK, не для магазина.

### Историческая сборка — web/PWA v134 clean desktop first run (05.11.2026)

Web/PWA v134 устраняет ложную сетевую ошибку первого запуска desktop-оболочки, когда прежней SQLite-базы ещё нет; приложение открывает локальные демо-данные без создания базы миграции. Улучшения адаптивности v132 и компактные WebP-обложки v133 сохранены. Python/SQLite 91/91, Web 63/63. Android APK 0.2.7 (versionCode 9) установлен поверх 0.2.6 на AVD API 36 без очистки данных и запущен. Физический телефон, аудио TalkBack/TTS, системное увеличение и private-mode поведение остаются открытыми.

SHA-256 APK: `8d81a1975c8aa65202518a451ec605c9fef21dc8e6c04cc13a6edf40acd065a9`. Это debug APK, не для магазина.

### Историческая сборка — Android 0.2.6 / web/PWA v133 compact cover assets (05.11.2026)

Web/PWA v133 настраивает dashboard для коротких экранов и высокого масштабирования: основные действия не попадают под нижнюю фиксированную навигацию. Уменьшенная по высоте layout проверена на 720×450 и 812×375; обычные мобильные размеры 320×568 и 390×844 сохранены. Web suite 63/63, Python/SQLite 91/91; APK 0.2.6 (versionCode 8) установлен поверх 0.2.5 на AVD API 36 без очистки данных и запущен. Физический телефон, аудио TalkBack/TTS, системное увеличение и private-mode поведение остаются открытыми.

SHA-256 APK: `3f54adfe4e7fa770470a689f9bad5f76352df35bf2e0dcb5f148747e8bef2a95`. Это debug APK, не для магазина.
