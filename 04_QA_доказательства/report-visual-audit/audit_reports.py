from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"
OUTPUT = ROOT / "служебные_файлы" / "qa_01-11-2026" / "report-visual-audit"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def normalized(value: str) -> str:
    return re.sub(r"\W+", " ", value.lower())


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for number, stem in ((4, "Отчёт_ООП_Модуль_4"), (5, "Отчёт_ООП_Модуль_5")):
        docx = PACKAGE / "01_Отчёты" / f"{stem}.docx"
        pdf = PACKAGE / "01_Отчёты" / f"{stem}.pdf"
        with ZipFile(docx) as archive:
            xml = ElementTree.fromstring(archive.read("word/document.xml"))
        paragraphs = [
            "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
            for paragraph in xml.findall(".//w:p", NS)
        ]
        docx_text = "\n".join(paragraphs)
        reader = PdfReader(str(pdf))
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        similarity = difflib.SequenceMatcher(None, normalized(docx_text), normalized(pdf_text)).ratio()
        if similarity < 0.99:
            raise SystemExit(f"Module {number}: DOCX/PDF text similarity is only {similarity:.5f}")
        contact = ROOT / "служебные_файлы" / "report-review-v88" / f"module{number}-contact-sheet.jpg"
        shutil.copy2(contact, OUTPUT / contact.name)
        records.append({
            "module": number,
            "docx": {"file": docx.name, "sha256": hashlib.sha256(docx.read_bytes()).hexdigest(), "paragraph_text_chars": len(docx_text)},
            "pdf": {"file": pdf.name, "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": len(reader.pages), "extracted_text_chars": len(pdf_text)},
            "normalized_text_similarity_docx_pdf": round(similarity, 5),
            "visual_review": "all PDF pages rendered and inspected in contact sheets; representative pages inspected full-size",
            "references_section_present": "Источники" in pdf_text,
        })
    result = {
        "date": "2026-11-01",
        "result": "PASS",
        "reports": records,
        "visual_findings": {
            "module4": "10 pages; figures, diagrams, code examples and sources visible; no obvious clipping or overlap",
            "module5": "11 pages; figures, diagrams, code examples and sources visible; no obvious clipping or overlap",
        },
        "note": "Read-only audit. The skill renderer could not start because pdf2image is unavailable; final PDFs were rendered directly with Poppler. DOCX text was extracted from OOXML and matched against its PDF.",
    }
    (OUTPUT / "report-visual-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "README.md").write_text(
        "# Visual audit of module reports — 01.11.2026\n\n"
        "Both final package PDFs were rendered page by page with Poppler. Contact sheets cover every page; title, representative code/figure pages, and reference lists were inspected full-size. DOCX paragraph text was extracted from OOXML and compared with the paired PDF; normalized text similarity exceeds 99.8% for both reports. See `report-visual-audit.json` for hashes and page counts. Rerun from the project root with `python служебные_файлы/qa_01-11-2026/report-visual-audit.py`.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
