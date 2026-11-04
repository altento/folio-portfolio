from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[3]
DOCX = ROOT / "Отчет_ООП_Модуль_4.docx"
OLD = "Python · Tkinter · SQLite · JSON / CSV"
NEW = "Python · Tkinter · JSON / CSV"
doc = Document(DOCX)
matches = [p for p in doc.paragraphs if OLD in p.text]
if len(matches) != 1:
    raise SystemExit(f"Expected one historic code listing, found {len(matches)}")
p = matches[0]
# Preserve paragraph/run styling by changing only the run containing the stack.
changed = False
for run in p.runs:
    if OLD in run.text:
        run.text = run.text.replace(OLD, NEW)
        changed = True
if not changed:
    # python-docx may split the target across runs; retain the paragraph style and replace paragraph text.
    text = p.text
    if OLD not in text:
        raise SystemExit("Target listing split across runs unexpectedly")
    for run in p.runs:
        run.text = ""
    p.runs[0].text = text.replace(OLD, NEW)

doc.save(DOCX)
print(f"Updated historical module 4 listing: {DOCX}")

