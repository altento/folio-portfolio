# Android AVD — Web/PWA v154, Android 0.3.17

Дата: 08.11.2026. APK `ru.folio.portfolio` версии 0.3.17 / versionCode 29 установлен на выделенный Android API 36 AVD через `adb install -r`. Приложение обновлялось поверх уже установленной версии; `uninstall`, очистка данных и wipe не выполнялись.

При первом запуске после обновления Service Worker показал штатное уведомление о доступной версии. Его кадр — [`dashboard.png`](dashboard.png). После команды перезапуска уведомление исчезло, главная страница и три демонстрационные карточки открылись — [`dashboard-after-update.png`](dashboard-after-update.png). Следующий холодный запуск точной версии 0.3.17 повторён автоматическим сценарием.

Встроенные файлы APK сверены: манифест версии 0.3.17/code 29, CSS v154 с минимальной высотой кнопки 44 px и Service Worker cache `folio-shell-v154-mobile-touch-targets`. После полной загрузки Android UIAutomator увидел 107 узлов, 18 именованных кликабельных элементов и 0 безымянных. XML-дерево сохранено в [`window-after-update.xml`](window-after-update.xml), сводка — [`ui-audit.json`](ui-audit.json).

Повторяемая проверка установки и запуска: [`run_android_v154_smoke.py`](run_android_v154_smoke.py); её результат, версии, хэши скриншотов и APK — [`result.json`](result.json). Текущий APK SHA-256: `dce9acee471bf8bab3f8a116d03964a2b01520526931e7c72f01e70508b2770d`.

Эмуляторный запуск не заменяет проверку на физическом телефоне. Речь и жесты TalkBack не принимались; debug APK не является магазинной release-сборкой.
