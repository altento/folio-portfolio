# Сортировка по тегам — v144

Внутри:
- `tag-sorting-v144-results.json` — Playwright desktop/mobile и saved-view результат.
- `projects-sorted-by-tags-v144.png`, `projects-sorted-by-tags-v144-390.png`, `projects-sorted-by-tags-v144-320.png` — desktop и мобильные кадры.
- `android-v144-home-clean.png`, `android-v144-offline.png`, `android-v144-offline-results.json` — установка, запуск и offline cold start APK 0.3.7/code 19.
- `run-tag-sort-v144.mjs` — воспроизводимый QA поток.

Все браузерные проверки использовали изолированный контекст с демонстрационными кейсами; пользовательская база не читалась и не изменялась. Android сеть до/после была включена, Wi‑Fi/mobile data отключались только на время cold-start проверки, затем исходные настройки восстановлены.
