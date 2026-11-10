from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
from PIL import Image, ImageDraw, ImageOps
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "служебные_файлы" / "qa_10-11-2026"
OUT = QA / "report-render-v161-final"
DOCX = ROOT / "Отчет_ООП_Модуль_5_v161.docx"
PDF = OUT / "Отчет_ООП_Модуль_5_v161.pdf"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def doc_text(path: Path) -> str:
    doc = Document(path)
    pieces = []
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:p"):
            pieces.append(Paragraph(element, doc).text)
        elif element.tag == qn("w:tbl"):
            table = Table(element, doc)
            for row in table.rows:
                pieces.extend(cell.text for cell in row.cells)
    return "\n".join(pieces)


def main() -> None:
    if not DOCX.is_file() or not PDF.is_file():
        raise FileNotFoundError("The current DOCX and its rendered PDF are required.")
    pages = sorted(OUT.glob("page-*.png"), key=lambda path: int(re.search(r"(\d+)$", path.stem).group(1)))
    pdf = PdfReader(str(PDF))
    if len(pages) != len(pdf.pages):
        raise RuntimeError(f"Rendered PNG count {len(pages)} differs from PDF pages {len(pdf.pages)}")
    if not pages or any(not re.sub(r"\s", "", page.extract_text() or "") for page in pdf.pages):
        raise RuntimeError("A report page has no extractable text.")
    thumbs = []
    sizes = []
    for i, path in enumerate(pages, 1):
        with Image.open(path) as source:
            source.verify()
        with Image.open(path) as source:
            image = source.convert("RGB")
            sizes.append(list(image.size))
            if image.width < 1200 or image.height < 1500:
                raise RuntimeError(f"Page render is below the minimum size: {path.name} {image.size}")
            image.thumbnail((306, 396), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (326, 424), "#f3f4f6")
            tile.paste(image, ((326 - image.width) // 2, 8))
            ImageDraw.Draw(tile).text((10, 404), f"Page {i:02d}", fill="#252525")
            thumbs.append(tile)
    columns = 4
    rows = (len(thumbs) + columns - 1) // columns
    contact = Image.new("RGB", (columns * 326, rows * 424), "#e8eaed")
    for index, tile in enumerate(thumbs):
        contact.paste(tile, ((index % columns) * 326, (index // columns) * 424))
    contact_path = OUT / "contact-sheet.png"
    contact.save(contact_path, format="PNG", optimize=True)
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    source_text = doc_text(DOCX)
    similarity = SequenceMatcher(None, re.sub(r"\s+", " ", source_text).strip(), re.sub(r"\s+", " ", pdf_text).strip()).ratio()
    summary = {
        "source_docx": DOCX.name,
        "source_docx_sha256": sha(DOCX),
        "rendered_pdf": PDF.name,
        "rendered_pdf_sha256": sha(PDF),
        "pdf_pages": len(pdf.pages),
        "rendered_png_pages": len(pages),
        "page_image_dimensions_px": sizes,
        "dpi": 144,
        "renderer": "render_docx.py with LibreOffice 26.8.2 (The Document Foundation signed MSI, temporary administrative extraction), then bundled Poppler",
        "all_pages_have_extractable_text": True,
        "docx_pdf_text_similarity": round(similarity, 6),
        "contact_sheet": contact_path.name,
        "contact_sheet_sha256": sha(contact_path),
    }
    (OUT / "render.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if similarity < 0.98:
        raise RuntimeError(f"DOCX/PDF normalized text similarity is too low: {similarity:.6f}")


if __name__ == "__main__":
    main()
