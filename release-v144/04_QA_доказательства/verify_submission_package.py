from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {"__pycache__"}
FORBIDDEN = {"portfolio_data.sqlite3", "portfolio_data.json"}


def python_result(output: str) -> int | None:
    match = re.search(r"Ran (\d+) tests?\b", output)
    return int(match.group(1)) if match and re.search(r"\bOK\b", output) else None


def web_result(output: str) -> tuple[int, int] | None:
    tests = re.search(r"ℹ tests (\d+)\s+ℹ suites \d+\s+ℹ pass (\d+)\s+ℹ fail 0", output)
    return (int(tests.group(1)), int(tests.group(2))) if tests else None


def included_files(package: Path) -> dict[str, Path]:
    result = {}
    for path in package.rglob("*"):
        if not path.is_file() or path.name == "manifest.sha256.json" or path.name.startswith("~$"):
            continue
        if path.parent.name == "01_Отчёты" and path.name in {"Отчет_ООП_Модуль_5.docx", "Отчет_ООП_Модуль_5.pdf"}:
            continue
        if EXCLUDED_DIRS.intersection(path.parts) or path.suffix == ".pyc":
            continue
        result[path.relative_to(package).as_posix()] = path
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the folio handoff folder and ZIP.")
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    package = args.package_dir.resolve()
    archive = args.archive.resolve()
    manifest_path = package / "manifest.sha256.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    records = manifest["files"]
    expected = {item["path"]: item for item in records}
    actual = included_files(package)
    if len(records) != manifest["file_count_excluding_manifest"]:
        raise SystemExit("Manifest file count does not match its entries.")
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        raise SystemExit(f"Folder/manifest mismatch. Missing={missing}; extra={extra}")
    if any(path.name in FORBIDDEN for path in package.rglob("*")):
        raise SystemExit("A personal database or JSON file is present in the package folder.")
    for relative, path in actual.items():
        record = expected[relative]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record["sha256"] or path.stat().st_size != record["size_bytes"]:
            raise SystemExit(f"File verification failed: {relative}")
    app_dir = package / "02_Приложение"
    python_run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=app_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    python_count = python_result(python_run.stdout)
    if python_run.returncode != 0 or python_count is None or python_count < 1:
        raise SystemExit("Packaged Python regression suite failed or reported no completed tests:\n" + python_run.stdout[-5000:])
    web_run = subprocess.run(
        ["npm", "test"],
        cwd=app_dir / "web",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=(sys.platform == "win32"),
    )
    web_counts = web_result(web_run.stdout)
    if web_run.returncode != 0 or web_counts is None or web_counts[0] < 1 or web_counts[0] != web_counts[1]:
        raise SystemExit("Packaged web regression suite failed or did not pass every test:\n" + web_run.stdout[-5000:])
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise SystemExit("ZIP CRC verification failed.")
        prefix = package.name + "/"
        zip_names = set(zipped.namelist())
        expected_names = {prefix + name for name in expected} | {prefix + "manifest.sha256.json"}
        if zip_names != expected_names:
            raise SystemExit("ZIP contents do not match the package folder.")
        if any(name.rsplit("/", 1)[-1] in FORBIDDEN for name in zip_names):
            raise SystemExit("A personal database or JSON file is present in the ZIP.")
        python_log = zipped.read(prefix + "04_QA_доказательства/python-regression-package.log").decode("utf-8", "replace")
        web_log = zipped.read(prefix + "04_QA_доказательства/web-regression-package.log").decode("utf-8", "replace")
        if python_result(python_log) != python_count:
            raise SystemExit("Stored Python regression log does not match the current run.")
        if web_result(web_log) != web_counts:
            raise SystemExit("Stored web regression log does not match the current run.")
    print(f"PASS: {len(expected)} files; folder hashes; ZIP member set and CRC; package Python tests {python_count}/{python_count}; package web tests {web_counts[0]}/{web_counts[0]}; user data excluded.")


if __name__ == "__main__":
    main()








