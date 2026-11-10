# Folio — локальный портфель проектов

## Актуальный комплект v144 — 10 ноября 2026

Последний проверенный пакет находится в папке [release-v144](release-v144/). Внутри — полные исходники, приложение для Windows/Web/Android, отчёты модулей ООП 4–5, исходные задания, инструкция и QA-доказательства.

- Web/PWA v161, Windows WebView2 v164, Android debug 0.3.24 / versionCode 36.
- Проверки: Python 97/97, Web 85/85, Windows EXE route matrix 20/20.
- Отчёты: модуль 4 — 12 страниц; модуль 5 — 18 страниц с полноразмерными кадрами всех страниц.
- Папка релиза содержит manifest и проверена по SHA-256, ZIP-member set, CRC и повторным тестам.
- [Скачать полный ZIP](Пакет_сдачи_портфолио_модули_4_5_на_проверку.zip) · [SHA-256](Пакет_сдачи_портфолио_модули_4_5_на_проверку.zip.sha256).
- [Подробный QA-отчёт](release-v144/Отчет_QA_10-11-2026.md) · [краткий старт](release-v144/СНАЧАЛА_ПРОЧИТАЙ.md).

## Windows: какой EXE запускать

Чтобы получить интерфейс как на сайте, запускай актуальную сборку [folio-desktop.exe v164](https://github.com/altento/folio-portfolio/tree/main/release-v144/02_Приложение/dist/folio-webview-v164/folio-desktop). Скачай и распакуй полный ZIP, сохранив рядом папку `_internal` — одного EXE для запуска недостаточно.

В комплекте также есть [02_Приложение/folio.exe](https://github.com/altento/folio-portfolio/blob/main/release-v144/02_Приложение/folio.exe): это старая учебная Tk-версия, у неё другой интерфейс. Веб-сайт и Windows-приложение хранят проекты отдельно; автоматической синхронизации нет, перенос делается через JSON.

Публичный сайт [GitHub Pages](https://altento.github.io/folio-portfolio/) обновлён до Web/PWA v161. Публикация выполнена коммитом [`3722f94`](https://github.com/altento/folio-portfolio/commit/3722f941cf9a3a0f3e8e9bccd8abf09aa48838aa); workflow [Deploy web app to GitHub Pages](https://github.com/altento/folio-portfolio/actions/runs/42760224009) завершился успешно. Отдельный [отчёт о публикации и проверке](deployment-v161.md) содержит результаты и QA-скриншоты. APK предназначен для локальной проверки и подписан debug-ключом.

Folio хранит данные локально. Персональные SQLite/JSON-базы в комплект не включены; JSON-резервная копия приложения содержит весь профиль и должна храниться приватно.