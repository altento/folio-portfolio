from __future__ import annotations

import hashlib
from pathlib import Path

from docx import Document
from docx.shared import Inches


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Отчет_ООП_Модуль_5_v160.docx"
REPORT = ROOT / "Отчет_ООП_Модуль_5_v161.docx"
SCREENSHOT = (
    ROOT / "служебные_файлы" / "qa_10-11-2026" / "web-v161-v164-regression"
    / "projects-1440x900.png"
)


def replace_paragraph(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run._element.getparent().remove(run._element)
    else:
        paragraph.add_run(text)


def main() -> None:
    if not SOURCE.is_file() or not SCREENSHOT.is_file():
        raise FileNotFoundError("The previous report or current project screenshot is missing.")
    doc = Document(SOURCE)
    if len(doc.paragraphs) < 75 or len(doc.tables) < 2:
        raise RuntimeError("Module 5 report structure changed; review before updating.")

    replace_paragraph(doc.paragraphs[69], "А.2 Проверки продуктовой сборки на 10.11.2026")
    replace_paragraph(
        doc.paragraphs[70],
        "Этот раздел фиксирует локальный продуктовый срез после учебного этапа модуля 5. Учебный настольный прототип и его алгоритмы описаны в основной части отчёта. В приложении приведены результаты Web/PWA v161, Windows WebView2 v164 и Android debug 0.3.24/code36.",
    )
    replace_paragraph(
        doc.paragraphs[71],
        "Матрица Web/PWA v161 выполнена в Chromium против локального EXE-хоста Windows WebView2 v164. Четыре раздела проверены при 320×568, 390×568, 390×844, 768×900 и 1440×900: 20/20 состояний прошли без переполнения, ошибок браузера и битых изображений; все касательные цели не меньше 44 CSS px. При ширине до 390 px минимальный размер измеренных подписей — 10 px. Закрытые мобильные фильтры и сохранённые подборки скрывают свои элементы; после раскрытия проверены доступные имена. В изолированном профиле создание, сохранение после перезагрузки, редактирование, Undo и окончательное удаление синтетического проекта прошли. Холодный офлайн-перезапуск загрузил три демонстрационные записи и обложки. Axe-core 4.14.0 проверил десять состояний: 0 автоматических нарушений и ошибок браузера; оставшиеся отметки color-contrast требуют ручной оценки наложения текста на изображения. Подпись dashboard получила непрозрачную тёмную подложку, градиент обложки кейса усилен для светлых пользовательских изображений. Android 0.3.24/code36 установлен поверх 0.3.23 на AVD API 36 без очистки данных. Обновление применено перезапуском, затем холодный запуск при Active default network: none подтвердил офлайн-ресурсы. UIAutomator видит только контейнер WebView; физический телефон и речь/жесты TalkBack этим прогоном не подтверждены.",
    )
    image_paragraph = doc.paragraphs[72]
    image_paragraph.clear()
    run = image_paragraph.add_run()
    shape = run.add_picture(str(SCREENSHOT), width=Inches(6.35))
    shape._inline.docPr.set("descr", "Каталог проектов Folio в Windows WebView2 v164 с фильтрами и тремя синтетическими карточками.")
    shape._inline.docPr.set("title", "Каталог проектов Folio WebView2 v164")
    replace_paragraph(
        doc.paragraphs[73],
        "Рисунок 8 — Каталог проектов Web/PWA v161 в оболочке Windows WebView2 v164. Снимок сделан 10.11.2026 при проверке локального кандидата.",
    )
    replace_paragraph(
        doc.paragraphs[74],
        "Протоколы, сценарии проверки и полноразмерные скриншоты находятся в разделе «04_QA-доказательства» сдачного пакета: матрица Web/PWA и Windows — web-v161-v164-regression, Android — android-v161, скан доступности — accessibility-v161-live. В тестах использовались только синтетические данные и изолированные профили.",
    )

    table = doc.tables[-1]
    if len(table.rows) != 5:
        raise RuntimeError("QA table row count changed; review before updating.")
    rows = [
        (
            "Web/PWA v161",
            "85/85 автоматизированных web-проверок пройдены. Axe-core 4.14.0: 0 нарушений в 10 состояниях; проверены имена кнопок, скрытие закрытых фильтров, размер подписей и контрастные подложки для текста на обложках.",
        ),
        (
            "Windows WebView2 v164",
            "20/20 сочетаний четырёх разделов и пяти размеров экрана. Переполнений, ошибок браузера, битых изображений и касательных целей меньше 44 px — 0; CRUD и холодная офлайн-перезагрузка проверены.",
        ),
        (
            "Android debug 0.3.24 / code 36",
            "Установлен поверх 0.3.23 на AVD Android API 36 без очистки данных. Баннер обновления применён перезапуском; холодный запуск при Active default network: none подтвердил локальные ресурсы. UIAutomator видит только контейнер WebView; физический телефон и TalkBack не проверялись.",
        ),
        (
            "Python / SQLite / web core",
            "97/97 проверок Python/SQLite и 85/85 проверок Web/PWA пройдены.",
        ),
    ]
    for row, values in zip(table.rows[1:], rows, strict=True):
        replace_paragraph(row.cells[0].paragraphs[0], values[0])
        replace_paragraph(row.cells[1].paragraphs[0], values[1])

    doc.paragraphs[71].paragraph_format.keep_together = True
    doc.save(REPORT)
    check = Document(REPORT)
    current_text = "\n".join(
        [check.paragraphs[i].text for i in range(69, 75)]
        + [row.cells[0].text + " " + row.cells[1].text for row in check.tables[-1].rows]
    )
    for stale in ("Web/PWA v160", "WebView2 v163", "code 35", "83/83"):
        if stale in current_text:
            raise RuntimeError(f"Stale release marker remains in current QA appendix: {stale}")
    print(f"Updated {REPORT.name}; screenshot SHA-256={hashlib.sha256(SCREENSHOT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
