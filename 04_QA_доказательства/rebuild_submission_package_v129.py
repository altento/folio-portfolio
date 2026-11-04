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
    phone_zip = ROOT / "folio-android-debug-for-phone.zip"
    if phone_zip.is_file():
        shutil.copy2(phone_zip, APP_PACKAGE / "mobile" / phone_zip.name)
    for name in ("main.py", "portfolio_core.py", "sqlite_storage.py", "requirements.txt", "Запустить приложение.bat", "build-desktop.ps1"):
        shutil.copy2(ROOT / name, APP_PACKAGE / name)
    desktop_exe = ROOT / "folio.exe"
    if desktop_exe.is_file():
        shutil.copy2(desktop_exe, APP_PACKAGE / "folio.exe")
    safe_mirror(ROOT / "tests", APP_PACKAGE / "tests",
                PACKAGE, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("README.md", "СНАЧАЛА_ПРОЧИТАЙ.md", "План_работ_продукт_и_отчеты.md", "Отчет_QA_02-11-2026.md",
                 "Матрица_требований_модулей_4_5.md", "Руководство_пользователя.md",
                 "Решение_публикация_и_синхронизация_29-10-2026.md",
                 "Решения_дизайна_и_UX.md", "Спецификация_продукта_v1.md"):
        source = ROOT / name
        target = PACKAGE / name
        if source.exists() and target.exists():
            shutil.copy2(source, target)
    documentation = PACKAGE / "03_Документация"
    publication_decision = ROOT / "Решение_публикация_и_синхронизация_29-10-2026.md"
    if publication_decision.is_file():
        shutil.copy2(publication_decision, PACKAGE / publication_decision.name)
        shutil.copy2(publication_decision, documentation / publication_decision.name)
    duplicate_exports = (
        "+Матрица_требований_модулей_4_5.md",
        "+Отчет_QA_02-11-2026.md",
        "+План_работ_продукт_и_отчеты.md",
        "+Руководство_пользователя.md",
        "+СНАЧАЛА_ПРОЧИТАЙ.md",
    )
    for name in duplicate_exports:
        duplicate = documentation / name
        if duplicate.is_file() and not duplicate.is_symlink():
            duplicate.unlink()
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
    stale_builder = QA_PACKAGE / "rebuild_submission_package_v113.py"
    previous_builder = QA_PACKAGE / "rebuild_submission_package_v128.py"
    older_builder = QA_PACKAGE / "rebuild_submission_package_v117.py"
    if older_builder.exists():
        older_builder.unlink()
    if previous_builder.exists():
        previous_builder.unlink()
    if stale_builder.exists():
        stale_builder.unlink()
    shutil.copy2(Path(__file__), QA_PACKAGE / "rebuild_submission_package_v129.py")

    for dirname in ("web-v93-storage-resilience", "android-v93-emulator-api36", "web-v93-accessibility", "web-accessibility-v97",
                    "web-responsive-v97", "web-responsive-v98", "web-responsive-v99", "web-csv-safety-v99", "web-import-size-v100",
                    "android-v99", "report-v94-evidence", "safe-import-v95", "safe-import-v97", "mobile-first-screen-v96",
                    "desktop-gallery-v97", "web-import-v97", "web-mobile-target-v101", "web-mobile-catalog-v102", "web-accessibility-v103", "web-offline-v103", "android-offline-v103", "web-offline-v104", "android-offline-v104", "android-v101", "android-v102", "mobile-case-form-wizard-v105", "cross-device-v110", "cross-device-v111", "web-live-v111", "web-live-v113", "report-v111-parity", "cover-focal-point-v113", "pwa-offline-v113", "web-accessibility-v114", "desktop-exe-v1", "android-v114-privacy-refresh", "web-accessibility-v115", "pwa-offline-v115", "android-v115-mobile-readability", "desktop-form-multiline-v115", "report-m4-pdf-render", "report-m5-precision-review", "web-responsive-v116", "android-v116-responsive", "web-showcase-v117", "android-v117-showcase", "desktop-keyboard-v118", "android-v118-private-storage", "android-accessibility-v120", "desktop-exe-v121", "android-accessibility-v125", "web-quota-error"):
        safe_mirror(QA / dirname, QA_PACKAGE / dirname, PACKAGE)

    shutil.copy2(QA / "Проверка_мобильного_каталога_v102.md",
                 QA_PACKAGE / "Проверка_мобильного_каталога_v102.md")

    # Keep any existing nested duplicate references in sync with the authoritative root copies.
    for name in (
        "План_работ_продукт_и_отчеты.md",
        "Отчет_QA_02-11-2026.md",
        "Матрица_требований_модулей_4_5.md",
        "СНАЧАЛА_ПРОЧИТАЙ.md",
    ):
        source = PACKAGE / name
        for target in PACKAGE.rglob(name):
            if target != source and source.is_file():
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


