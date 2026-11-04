from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

QA = Path(__file__).resolve().parent
PACKAGE = QA.parent
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
EXTERNAL_SCHEMES = ("http:", "https:", "mailto:", "tel:")
checked: list[dict[str, str]] = []
broken: list[dict[str, str]] = []
outside: list[dict[str, str]] = []

for markdown in PACKAGE.rglob("*.md"):
    source = markdown.read_text(encoding="utf-8-sig", errors="replace")
    for raw_target in LINK.findall(source):
        target = raw_target.strip().split()[0].strip("<>")
        if not target or target.startswith(("#", *EXTERNAL_SCHEMES)):
            continue
        local_path = urllib.parse.unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not local_path:
            continue
        resolved = (markdown.parent / local_path).resolve()
        record = {"file": markdown.relative_to(PACKAGE).as_posix(), "target": target}
        checked.append(record)
        try:
            resolved.relative_to(PACKAGE.resolve())
        except ValueError:
            outside.append(record)
        else:
            if not resolved.exists():
                broken.append(record)

result = {
    "markdown_files": len(list(PACKAGE.rglob("*.md"))),
    "relative_links_checked": len(checked),
    "broken_links": broken,
    "links_outside_package": outside,
    "passed": not broken and not outside,
}
(QA / "markdown-links-v49-results.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"{'PASS' if result['passed'] else 'FAIL'}: {len(checked)} package-relative Markdown links; broken={len(broken)}; outside={len(outside)}")
if not result["passed"]:
    raise SystemExit(1)
