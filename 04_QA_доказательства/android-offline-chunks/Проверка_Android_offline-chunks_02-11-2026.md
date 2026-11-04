# Android: сборка и холодный офлайн-запуск

Дата проверки: 02.11.2026.

## Изменение

Android-сборка объединяет `web/app.js` через esbuild с code splitting. В `app.js` native startup bridge загружается отдельным динамическим chunk до регистрации/обновления Service Worker. Раньше precache содержал исходные `app.js`, `native-export.js`, но не сгенерированные хешированные chunks. При первом холодном запуске без сети Service Worker мог не иметь локальной копии startup chunk.

`mobile/scripts/build-web.mjs` теперь находит все `.js` под `mobile/www/chunks/` и добавляет их относительные пути в precache списка Service Worker, созданного в `mobile/www/sw.js`. Папочный `web/sw.js` повышен до `folio-shell-v90-offline-chunks` и включает исходный `native-startup.js` для обычной web-сборки.

## Результат

- `npm run build:web` — PASS.
- `npm run android:sync` — PASS; ресурсы скопированы в `mobile/android/app/src/main/assets/public`.
- В сгенерированном Service Worker перечислены 3 chunk: `chunk-COP62JR2.js`, `native-export-HYZRL5U2.js`, `native-startup-P3VUY4L5.js`; все 3 файла присутствуют в Android web assets.
- `npm run android:debug` — PASS после запуска штатного `mobile/build-android.ps1`, который выбирает Temurin JDK 21 и короткий временный каталог для Windows AF_UNIX sockets.
- APK установлен и запущен на Android Emulator API 36 (`sdk_gphone64_x86_64`). Wi-Fi и мобильная передача данных отключены; после force-stop приложение запущено повторно, открыло рабочую область и демонстрационные кейсы.
- `apksigner verify`: подпись debug, Android APK Signature Scheme v2 — PASS.
- `zipalign -c -v 4` — PASS.
- `py -3.13 -m unittest discover -s tests -v` — 58/58 PASS.
- `npm test` в `web/` — 26/26 PASS.

## Контрольные суммы

- APK SHA-256: `04c80c870c9c69bcfa34c11b4557f547f0eb4db4fea45a3ba08316c123bc8e7a`.
- Скриншот offline-повторного запуска SHA-256: `fafe0386f1a6d30399c0b5ad4cd2740d0ed088829d8847842b516bed74115cc7`.
- APK: `mobile/folio-android-debug.apk`.
- Скриншот: `служебные_файлы/qa_02-11-2026/android-offline-chunks/folio-v90-cold-offline.png`.

Проверка подтверждает сценарий на эмуляторе; физический телефон, OEM file picker и скринридер на физическом устройстве остаются открытыми пунктами.
