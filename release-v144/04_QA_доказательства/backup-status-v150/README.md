# Folio v150 — JSON backup status and Windows WebView2 host fix

Дата: 06.11.2026. Проверка использует только временный профиль и три демонстрационные записи.

## Обнаруженный дефект и исправление

Первый packaged v150 запуск в изолированном Windows WebView2 профиле зависал на стартовом экране. Причина найдена в локальном HTTP-хосте: `app.js` импортирует `backup-status.js`, но этот файл не входил в `STATIC_FILES` allowlist `desktop_webview.py`, поэтому WebView2 не мог завершить загрузку ES-модуля. Файл добавлен в allowlist и добавлен Python host regression test `test_serves_backup_status_module_imported_by_app`.

После исправления Windows WebView2 v150 был полностью пересобран. Точная собранная onedir версия повторно открылась с `--profile-dir` во временной папке; UIA показывает рабочий обзор, демо-портфолио из 3 записей, карточки, метрики и основной desktop layout. Это подтверждает первый запуск и отрисовку dashboard на Windows. В том же профиле вручную открыт экран «Настройки и данные»; UIA показал статус «Резервная копия не отмечена» и пояснение о проверке файла в загрузках. Экспорт намеренно не запускался, чтобы не писать файл в пользовательскую папку Downloads. Другие маршруты/действия не подтверждены этим smoke-test.

## Regression

- Python/SQLite и desktop host: 93/93, включая раздачу `backup-status.js` (06.11.2026).
- Web/PWA: 75/75 (06.11.2026).
- Личный профиль пользователя и персональная база не использовались.

## JSON-copy status

Новые unit tests проверяют переход current → stale по revision, обработку ошибочной метки и отказ persistent localStorage. В GUI подтверждены настройки и состояние «Резервная копия не отмечена». Экспорт файла не выполнялся, поэтому наличие JSON-файла не заявляется. Автоматические тесты проверяют revision transitions и отказ persistent localStorage.

## Артефакты и пределы

- Desktop release: `dist/folio-webview-v150/folio-desktop/folio-desktop.exe`, собран после исправления allowlist.
- Android: debug 0.3.13 / versionCode 25; APK SHA-256 `b3d2dbc1bbaf121a69d0994d5622a20c176c7e08f149b946b6c07143b8ac3655`.
- Android v150 runtime, физический телефон, TalkBack/TTS, системный zoom, Narrator и полная приёмка пользователем не проверены.
- Новая публикация не выполнялась; GitHub Pages остаётся на v120.
