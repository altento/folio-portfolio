# Windows WebView2 v146 — изолированный GUI smoke

Одноразовая QA-оболочка собрана PyInstaller из текущего `desktop_webview.py` и web/assets v146, с профилем `%TEMP%\folio-webview-v146-qa-profile` и loopback-портом 41946. Запущенное окно показало dashboard и 3 демо-кейса; UIA tree доступен. Это изолированный GUI smoke конфигурации того же desktop host, а не запуск пользовательской установки/профиля.

Снимок: `windows-v146-isolated-home.jpg`; протокол: `windows-v146-isolated-results.json`; одноразовый launcher source: `folio_webview_qa_v146.py`. Сам disposable binary хранится в Temp и в сдачный пакет не включён.
