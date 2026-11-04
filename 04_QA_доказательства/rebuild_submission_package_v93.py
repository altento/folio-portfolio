from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"
ARCHIVE = ROOT / f"{PACKAGE.name}.zip"
WEB = ROOT / "web"
MOBILE = ROOT / "mobile"
QA = ROOT / "служебные_файлы" / "qa_02-11-2026"
QA_PACKAGE = PACKAGE / "04_QA_доказательства"
APP_PACKAGE = PACKAGE / "02_Приложение"
MANIFEST = PACKAGE / "manifest.sha256.json"
FORBIDDEN = {"portfolio_data.sqlite3", "portfolio_data.json"}


def safe_mirror(source: Path, target: Path, package_root: Path, ignore=None) -> None:
    target_resolved = target.resolve()
    if not target_resolved.is_relative_to(package_root.resolve()):
        raise RuntimeError(f"Refusing to mirror outside package: {target_resolved}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=ignore)


def included_files() -> dict[str, Path]:
    result = {}
    for path in PACKAGE.rglob("*"):
        if not path.is_file() or path == MANIFEST or path.name.startswith("~$"):
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.parent.name == "01_Отчёты" and path.name in {
            "Отчет_ООП_Модуль_5.docx",
            "Отчет_ООП_Модуль_5.pdf",
        }:
            continue
        result[path.relative_to(PACKAGE).as_posix()] = path
    return result


def build_manifest() -> int:
    files = included_files()
    entries = []
    for relative, path in sorted(files.items()):
        entries.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest = {
        "package": PACKAGE.name,
        "file_count_excluding_manifest": len(entries),
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(entries)


def build_archive() -> str:
    temporary = ARCHIVE.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative, path in sorted(included_files().items()):
            archive.write(path, f"{PACKAGE.name}/{relative}")
        archive.write(MANIFEST, f"{PACKAGE.name}/manifest.sha256.json")
    temporary.replace(ARCHIVE)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    sidecar = ARCHIVE.with_suffix(ARCHIVE.suffix + ".sha256")
    sidecar.write_bytes(f"{digest}  {ARCHIVE.name}\n".encode("utf-8"))
    return digest


def run_suite(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            shell=(sys.platform == "win32" and command[0] == "npm"))
    if result.returncode:
        raise RuntimeError(f"Command failed: {command}\n{result.stdout[-6000:]}")
    return result.stdout


def main() -> None:
    APP_PACKAGE.mkdir(parents=True, exist_ok=True)
    QA_PACKAGE.mkdir(parents=True, exist_ok=True)

    safe_mirror(WEB, APP_PACKAGE / "web", PACKAGE)
    safe_mirror(MOBILE, APP_PACKAGE / "mobile", PACKAGE,
                ignore=shutil.ignore_patterns("node_modules", ".gradle", "build", "__pycache__", "*.pyc"))
    for name in ("README.md", "СНАЧАЛА_ПРОЧИТАЙ.md", "План_работ_продукт_и_отчеты.md", "Отчет_QA_02-11-2026.md",
                 "Матрица_требований_модулей_4_5.md", "Руководство_пользователя.md",
                 "Решения_дизайна_и_UX.md", "Спецификация_продукта_v1.md"):
        source = ROOT / name
        target = PACKAGE / name
        if source.exists() and target.exists():
            shutil.copy2(source, target)
    report_names = {
        "Отчет_ООП_Модуль_4.docx": "Отчёт_ООП_Модуль_4.docx",
        "Отчет_ООП_Модуль_4.pdf": "Отчёт_ООП_Модуль_4.pdf",
        "Отчет_ООП_Модуль_5.docx": "Отчёт_ООП_Модуль_5.docx",
        "Отчет_ООП_Модуль_5.pdf": "Отчёт_ООП_Модуль_5.pdf",
    }
    reports_dir = PACKAGE / "01_Отчёты"
    for source_name, package_name in report_names.items():
        source = ROOT / source_name
        target = reports_dir / package_name
        if source.exists() and target.exists():
            shutil.copy2(source, target)
    shutil.copy2(Path(__file__), QA_PACKAGE / "rebuild_submission_package_v93.py")

    for dirname in ("web-v93-storage-resilience", "android-v93-emulator-api36", "web-v93-accessibility",
                    "report-v94-evidence"):
        safe_mirror(QA / dirname, QA_PACKAGE / dirname, PACKAGE)

    # Keep any existing nested duplicate references in sync with the authoritative root copies.
    for name in ("План_работ_продукт_и_отчеты.md", "Отчет_QA_02-11-2026.md"):
        source = PACKAGE / name
        for target in PACKAGE.rglob(name):
            if target != source:
                shutil.copy2(source, target)

    python_log = run_suite([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], APP_PACKAGE)
    web_log = run_suite(["npm", "test"], APP_PACKAGE / "web")
    (QA_PACKAGE / "python-regression-package.log").write_text(python_log, encoding="utf-8")
    (QA_PACKAGE / "web-regression-package.log").write_text(web_log, encoding="utf-8")

    if any(path.name in FORBIDDEN for path in PACKAGE.rglob("*")):
        raise RuntimeError("A personal database or JSON file is present in the package.")
    count = build_manifest()
    digest = build_archive()
    verifier = QA_PACKAGE / "verify_submission_package.py"
    result = subprocess.run([sys.executable, str(verifier), "--package-dir", str(PACKAGE), "--archive", str(ARCHIVE)],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("Submission package verification failed:\n" + result.stdout[-8000:])
    print(result.stdout.strip())
    print(f"ZIP SHA-256: {digest}")
    print(f"Package folder files excluding manifest: {count}")


if __name__ == "__main__":
    main()
