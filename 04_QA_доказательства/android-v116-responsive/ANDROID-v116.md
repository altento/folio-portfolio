# Android v116 — итог проверки сборки

Дата: 02.11.2026  
Пакет: `ru.folio.portfolio`, Android debug APK  
Эмулятор: Android Emulator API 36, `emulator-5554`

## Артефакт

- APK: `mobile/folio-android-debug.apk`
- SHA-256: `8af6d74c4aad68099fbdb9ef36a4a39aed700ad9609a15da1cd0a3fc70b93d44`
- Размер телефонного ZIP: 18,107,672 байта; проверка ZIP и равенства APK по SHA-256 выполнена скриптом `mobile/refresh-android-delivery.py`.
- `assembleDebug`: BUILD SUCCESSFUL.
- Установка поверх предыдущей версии на AVD: PASS; Activity запущена.
- APK Signature Scheme v2: PASS; сертификат — Android Debug.
- `zipalign -c -v 4`: PASS.
- `allowBackup=false`; правила cloud backup и device transfer исключают пользовательские данные, включая локальные базы и хранилища.

## Проверенные сценарии

- После установки приложение запущено, а ожидающее обновление применено штатной кнопкой «Перезапустить».
- В landscape на AVD лента меню прокручивается касательным жестом независимо от основной страницы. После прокрутки доступны «Настройки и данные» и профиль; ширина документа не увеличилась. Машинные измерения в Chromium при 864×420 CSS px: `scrollTop` меню изменился с 0 на 87 px, `overflow-y: auto`, `documentWidth=864`.
- Снимок установленного приложения в landscape: `android-v116-current-screen.jpg`.
- Снимок доступного нижнего блока боковой навигации после touch-scroll: `android-v116-landscape-sidebar-scroll.jpg`.
- После выключения Wi-Fi и mobile data, при `airplane_mode_on=1` и `Active default network: none`, выполнены force-stop и повторный холодный запуск. Главный экран с демо-проектами открылся офлайн; кадр — `android-v116-cold-offline.jpg`. Команда эмулятора отказала в ручной отправке защищённого broadcast (exit 255), но системное значение авиарежима равно `1`, а `dumpsys connectivity` подтверждает отсутствие активной сети.
- Браузерный сценарий уменьшенной высоты viewport для имитации клавиатуры при 320×330 CSS px оставляет поле с фокусом полностью видимым (`y=272..318`, высота 46 px), ширина документа — 320 px. Кадр и данные: `../web-responsive-v116/form-keyboard-focus-320x330-v116.png` и `../web-responsive-v116/virtual-keyboard-results-v116.json`.

## Ограничения

Обычную экранную клавиатуру, физический телефон, TalkBack и системное увеличение не проверяли: Gboard на AVD в этом сеансе показывал экран ознакомления с рукописным вводом. Результат 320×330 — проверка поведения при уменьшении visual viewport в Chromium, не подтверждение реального ввода через Gboard.

