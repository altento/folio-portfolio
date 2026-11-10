# Отчёт проверки Android Folio 0.3.24 / versionCode 36

Дата: 10.11.2026. Проверена debug-сборка `ru.folio.portfolio` 0.3.24 (versionCode 36), содержащая ресурсы Web/PWA v161.

## Среда и обновление

- Android Emulator, AVD API 36, экран 1080×2400 px, плотность 420 dpi; устройство `emulator-5554`.
- APK установлен поверх версии 0.3.23 без очистки данных и удаления приложения.
- Состояние установленного пакета подтверждено через `adb shell dumpsys package`: `versionName=0.3.24`, `versionCode=36`.
- После обновления показано уведомление о новых ресурсах; после перезапуска Folio открыл dashboard и локальные изображения.
- Дерево UIAutomator сохранено отдельно. Оно содержит контейнер `android.webkit.WebView`, но не раскрывает DOM-элементы приложения.

## Офлайн-сценарий и восстановление сети

1. Перед холодным запуском сохранён `dumpsys connectivity` с состоянием `Active default network: none`.
2. Folio остановлено и запущено через launcher при отключённых Wi‑Fi и мобильных данных.
3. Dashboard и локальные обложки загрузились без активной сети; сетевых ошибок в самом приложении не наблюдалось.
4. После снимка сети включены обратно. `restored-connectivity.txt` подтверждает активное соединение Wi‑Fi.

## Снимки и протоколы

- `android-v161/after-update.png` — экран после установки 0.3.24.
- `android-v161/updated-dashboard.png` — Folio после применения обновления ресурсов.
- `android-v161/offline-cold-launch.png` — холодный запуск при `Active default network: none`.
- `android-v161/online-connectivity.txt`, `offline-connectivity.txt`, `restored-connectivity.txt` — состояния сети до и после.
- `android-v161/uiautomator.xml` — дерево Android UIAutomator.

## Контрольные суммы

- `mobile/folio-android-debug.apk`: 6,050,496 байт; SHA-256 `4e658f6abdfd5ec8dfd47865597c02996a03ce23cc84452f7a35183564cf8cb7`.
- `folio-android-debug-for-phone.zip`: 5,678,286 байт; SHA-256 `be77be46ac0cbec21e7af2a091dc519d372beb9d215ab63ee329cd4218d59b55`.

## Границы проверки

Подтверждены обновление без очистки данных, применение ресурсов, холодный офлайн-запуск на AVD и восстановление сети. Физический смартфон, OEM-диалог выбора файла и реальное озвучивание/жесты TalkBack не проверялись. APK подписан debug-ключом и предназначен для локальной проверки, не для Google Play.
