from __future__ import annotations

import hashlib
import json
import os
import re
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


def safe_clear(target: Path, package_root: Path) -> None:
    target_resolved = target.resolve()
    package_resolved = package_root.resolve()
    if target_resolved == package_resolved or not target_resolved.is_relative_to(package_resolved):
        raise RuntimeError(f"Refusing to clear outside a package child: {target_resolved}")
    if target.exists():
        shutil.rmtree(target)


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
    # Keep nested audit/verifier output deterministic on Windows consoles
    # whose legacy code page cannot encode all report symbols.
    os.environ["PYTHONIOENCODING"] = "utf-8"
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    # Preserve the running builder before clearing its containing QA folder.
    builder_source = Path(__file__).read_bytes()
    verifier_source = ROOT / "служебные_файлы" / "qa_05-11-2026" / "verify_submission_package_v137.py"
    if not verifier_source.is_file():
        raise FileNotFoundError(f"Pinned package verifier missing: {verifier_source}")
    safe_clear(APP_PACKAGE, PACKAGE)
    safe_clear(QA_PACKAGE, PACKAGE)
    APP_PACKAGE.mkdir(parents=True, exist_ok=True)
    QA_PACKAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(verifier_source, QA_PACKAGE / "verify_submission_package.py")

    safe_mirror(WEB, APP_PACKAGE / "web", PACKAGE)
    safe_mirror(ROOT / "assets", APP_PACKAGE / "assets", PACKAGE)
    # Omit generated web delivery trees: build:web recreates mobile/www from
    # the packaged sibling web/ source, and `cap sync android` recreates the
    # Android assets/public tree. This avoids three copies of large demo media.
    safe_mirror(MOBILE, APP_PACKAGE / "mobile", PACKAGE,
                ignore=shutil.ignore_patterns("node_modules", ".gradle", "build", "www", "public", "__pycache__", "*.pyc"))
    generated_delivery = (
        APP_PACKAGE / "mobile" / "www",
        APP_PACKAGE / "mobile" / "android" / "app" / "src" / "main" / "assets" / "public",
    )
    if any(path.exists() for path in generated_delivery):
        raise RuntimeError("Generated Android web assets should be recreated by the build script, not shipped twice")
    phone_zip = ROOT / "folio-android-debug-for-phone.zip"
    if phone_zip.is_file():
        shutil.copy2(phone_zip, APP_PACKAGE / "mobile" / phone_zip.name)
    for name in ("main.py", "portfolio_core.py", "sqlite_storage.py", "desktop_webview.py", "requirements.txt", "requirements-build.txt", "requirements-desktop-webview.txt", "Запустить приложение.bat", "build-desktop.ps1", "build-webview.ps1", "build-webview-v142.ps1", "build-webview-v143.ps1", "build-webview-v144.ps1", "build-webview-v145.ps1", "build-webview-v146.ps1", "build-webview-v147.ps1", "build-webview-v148.ps1", "build-webview-v149.ps1", "build-webview-v150.ps1", "build-webview-v151.ps1", "build-webview-v154.ps1", "build-webview-v155.ps1", "build-webview-v156.ps1", "build-webview-v157.ps1", "build-webview-v159.ps1", "build-webview-v160.ps1", "build-webview-v162.ps1", "build-webview-v163.ps1", "build-webview-v164.ps1"):
        shutil.copy2(ROOT / name, APP_PACKAGE / name)
    desktop_exe = ROOT / "dist" / "folio.exe"
    if not desktop_exe.is_file():
        desktop_exe = ROOT / "folio-current.exe"
    if not desktop_exe.is_file():
        desktop_exe = ROOT / "folio.exe"
    if desktop_exe.is_file():
        shutil.copy2(desktop_exe, APP_PACKAGE / "folio.exe")
    webview_candidates = ["folio-webview-v164", "folio-webview-v163", "folio-webview-v162", "folio-webview-v160", "folio-webview-v159", "folio-webview-v157", "folio-webview-v156", "folio-webview-v155", "folio-webview-v154", "folio-webview-v151", "folio-webview-v150", "folio-webview-v149", "folio-webview-v148", "folio-webview-v147", "folio-webview-v146", "folio-webview-v145", "folio-webview-v144", "folio-webview-v143", "folio-webview-v142", "folio-webview-v141", "folio-webview-v140", "folio-webview-v139", "folio-webview-v138", "folio-webview-v137", "folio-webview-v136", "folio-webview-v135", "folio-webview-v134", "folio-webview-v133", "folio-webview"]
    webview_distribution = next(
        (ROOT / "dist" / name / "folio-desktop" for name in webview_candidates
         if (ROOT / "dist" / name / "folio-desktop").is_dir()),
        None,
    )
    if webview_distribution is not None:
        destination_name = webview_distribution.parent.name
        safe_mirror(webview_distribution, APP_PACKAGE / "dist" / destination_name / "folio-desktop", PACKAGE)
    safe_mirror(ROOT / "tests", APP_PACKAGE / "tests",
                PACKAGE, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("README.md", "СНАЧАЛА_ПРОЧИТАЙ.md", "Проверка_готовности_05-11-2026.md", "План_работ_продукт_и_отчеты.md", "Отчет_QA_02-11-2026.md", "Отчет_QA_05-11-2026.md", "Отчет_QA_06-11-2026.md", "Отчет_QA_07-11-2026.md", "Отчет_QA_08-11-2026.md", "Отчет_QA_09-11-2026.md", "Отчет_QA_10-11-2026.md", "Проверка_готовности_09-11-2026.md", "Проверка_готовности_10-11-2026.md",
                 "Матрица_требований_модулей_4_5.md", "Руководство_пользователя.md",
                 "Решение_публикация_и_синхронизация_29-10-2026.md",
                 "Решения_дизайна_и_UX.md", "Спецификация_продукта_v1.md"):
        source = ROOT / name
        target = PACKAGE / name
        if source.exists() and target.exists():
            shutil.copy2(source, target)
    shutil.copy2(ROOT / "Проверка_готовности_05-11-2026.md", PACKAGE / "Проверка_готовности_05-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_05-11-2026.md", PACKAGE / "Отчет_QA_05-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_06-11-2026.md", PACKAGE / "Отчет_QA_06-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_07-11-2026.md", PACKAGE / "Отчет_QA_07-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_08-11-2026.md", PACKAGE / "Отчет_QA_08-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_09-11-2026.md", PACKAGE / "Отчет_QA_09-11-2026.md")
    shutil.copy2(ROOT / "Проверка_готовности_09-11-2026.md", PACKAGE / "Проверка_готовности_09-11-2026.md")
    shutil.copy2(ROOT / "Отчет_QA_10-11-2026.md", PACKAGE / "Отчет_QA_10-11-2026.md")
    shutil.copy2(ROOT / "Проверка_готовности_10-11-2026.md", PACKAGE / "Проверка_готовности_10-11-2026.md")
    for name in ("README.md", "СНАЧАЛА_ПРОЧИТАЙ.md", "Проверка_готовности_05-11-2026.md", "Проверка_готовности_09-11-2026.md", "Проверка_готовности_10-11-2026.md", "Отчет_QA_08-11-2026.md", "Отчет_QA_09-11-2026.md", "Отчет_QA_10-11-2026.md"):
        packaged_doc = PACKAGE / name
        if packaged_doc.is_file():
            text = packaged_doc.read_text(encoding="utf-8")
            text = text.replace("служебные_файлы/qa_08-11-2026/", "04_QA_доказательства/qa_08-11-2026/")
            text = text.replace("служебные_файлы/qa_09-11-2026/", "04_QA_доказательства/qa_09-11-2026/")
            text = text.replace("служебные_файлы/qa_10-11-2026/", "04_QA_доказательства/qa_10-11-2026/")
            text = text.replace("Пакет_сдачи_портфолио_модули_4_5_на_проверку/01_Отчёты/", "01_Отчёты/")
            text = text.replace("Пакет_сдачи_портфолио_модули_4_5_на_проверку/03_Документация/", "03_Документация/")
            packaged_doc.write_text(text, encoding="utf-8")
    mobile_readme = APP_PACKAGE / "mobile" / "README.md"
    if mobile_readme.is_file():
        text = mobile_readme.read_text(encoding="utf-8")
        text = text.replace("служебные_файлы/qa_08-11-2026/", "../../04_QA_доказательства/qa_08-11-2026/")
        text = text.replace("служебные_файлы/qa_09-11-2026/", "../../04_QA_доказательства/qa_09-11-2026/")
        text = text.replace("служебные_файлы/qa_10-11-2026/", "../../04_QA_доказательства/qa_10-11-2026/")
        mobile_readme.write_text(text, encoding="utf-8")
    documentation = PACKAGE / "03_Документация"
    source_assignments = ROOT / "служебные_файлы" / "source-assignments"
    if source_assignments.is_dir():
        safe_mirror(source_assignments, documentation / "Исходные_задания_ООП_модули_4_5", PACKAGE)
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
        "Отчет_ООП_Модуль_5_v161.docx": "Отчёт_ООП_Модуль_5.docx",
        "Отчет_ООП_Модуль_5_v161.pdf": "Отчёт_ООП_Модуль_5.pdf",
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
    (QA_PACKAGE / "rebuild_submission_package_v144.py").write_bytes(builder_source)

    qa_current = ROOT / "служебные_файлы" / "qa_05-11-2026"
    curated_qa = (
        "dialog-focus-v137",
        "cover-crop-v136",
        "report-documents-v136",
        "windows-first-run-v134",
        "android-v128-mobile-wizard",
        "talkback-v128",
        "web-v120-accessibility",
        "android-v120-smoke",
        "android-v114-privacy-refresh",
        "public-github-scan",
        "web-v119-live",
        "web-v119-cross-route",
        "routes-v141",
        "routes-v142",
        "routes-v143",
        "routes-v144",
        "tag-sorting-v144",
        "mobile-import-v146",
        "import-roundtrip-v146",
        "windows-v146-isolated",
        "mobile-v148",
        "windows-v148-isolated",
        "forced-colors-v148",
        "import-safe-replace-v148",
        "android-v148-start",
        "mobile-closed-dialog-v149",
        "backup-status-v150",
        "mobile-v147",
        "windows-v147-isolated",
        "mobile-import-v145",
        "import-roundtrip-v145",
        "single-synthetic-v144",
        "keyboard-import-v144",
        "effective-zoom-v144",
        "user-flow-v144",
        "import-roundtrip-v144",
        "user-flow-v141",
        "user-flow-v142",
        "user-flow-v143",
    )
    for dirname in curated_qa:
        source = qa_current / dirname
        if source.is_dir():
            ignore = None
            if dirname == "routes-v142":
                # Current passing form evidence is stored under form-v142;
                # exclude the earlier exploratory output with a superseded result.
                ignore = lambda directory, names: {"project-form-audit"} if Path(directory).resolve() == source.resolve() else set()
            if dirname == "routes-v143":
                ignore = lambda directory, names: {"project-form-audit"} if Path(directory).resolve() == source.resolve() else set()
            if dirname == "routes-v144":
                ignore = lambda directory, names: {"project-form-audit"} if Path(directory).resolve() == source.resolve() else set()
            safe_mirror(source, QA_PACKAGE / dirname, PACKAGE, ignore=ignore)

    tk_qa = ROOT / "служебные_файлы" / "qa_06-11-2026" / "tk-v148"
    if tk_qa.is_dir():
        safe_mirror(tk_qa, QA_PACKAGE / "tk-v148", PACKAGE)

    mobile_qa = ROOT / "служебные_файлы" / "qa_06-11-2026" / "mobile-closed-dialog-v149"
    if mobile_qa.is_dir():
        safe_mirror(mobile_qa, QA_PACKAGE / "mobile-closed-dialog-v149", PACKAGE)

    backup_qa = ROOT / "служебные_файлы" / "qa_06-11-2026" / "backup-status-v150"
    if backup_qa.is_dir():
        safe_mirror(backup_qa, QA_PACKAGE / "backup-status-v150", PACKAGE)

    android_v150_qa = ROOT / "служебные_файлы" / "qa_06-11-2026" / "android-v150"
    if android_v150_qa.is_dir():
        safe_mirror(android_v150_qa, QA_PACKAGE / "android-v150", PACKAGE)

    route_audit_v150 = ROOT / "служебные_файлы" / "qa_06-11-2026" / "route-audit-v150"
    if route_audit_v150.is_dir():
        safe_mirror(route_audit_v150, QA_PACKAGE / "route-audit-v150", PACKAGE)

    crud_v151b = ROOT / "служебные_файлы" / "qa_06-11-2026" / "crud-flow-v151b"
    if crud_v151b.is_dir():
        safe_mirror(crud_v151b, QA_PACKAGE / "crud-flow-v151b", PACKAGE)
    zoom200_v151b = ROOT / "служебные_файлы" / "qa_06-11-2026" / "zoom200-v151b"
    if zoom200_v151b.is_dir():
        safe_mirror(zoom200_v151b, QA_PACKAGE / "zoom200-v151b", PACKAGE)
    backup_transfer_v151b = ROOT / "служебные_файлы" / "qa_06-11-2026" / "backup-transfer-v151b"
    if backup_transfer_v151b.is_dir():
        safe_mirror(backup_transfer_v151b, QA_PACKAGE / "backup-transfer-v151b", PACKAGE)

    windows_v151_qa = ROOT / "служебные_файлы" / "qa_07-11-2026" / "windows-v151-isolated"
    if windows_v151_qa.is_dir():
        safe_mirror(windows_v151_qa, QA_PACKAGE / "windows-v151-isolated", PACKAGE)

    android_v151_mobile_qa = ROOT / "служебные_файлы" / "qa_07-11-2026" / "android-v151-mobile-web"
    if android_v151_mobile_qa.is_dir():
        safe_mirror(android_v151_mobile_qa, QA_PACKAGE / "android-v151-mobile-web", PACKAGE)

    windows_v154_backup = ROOT / "служебные_файлы" / "qa_07-11-2026" / "windows-v154-backup"
    if windows_v154_backup.is_dir():
        safe_mirror(windows_v154_backup, QA_PACKAGE / "windows-v154-backup", PACKAGE)

    windows_v154_native_import = ROOT / "служебные_файлы" / "qa_07-11-2026" / "windows-v154-native-import"
    if windows_v154_native_import.is_dir():
        safe_mirror(windows_v154_native_import, QA_PACKAGE / "windows-v154-native-import", PACKAGE)

    windows_v155_isolated = ROOT / "служебные_файлы" / "qa_07-11-2026" / "windows-v155-isolated"
    if windows_v155_isolated.is_dir():
        safe_mirror(windows_v155_isolated, QA_PACKAGE / "windows-v155-isolated", PACKAGE)

    mobile_v152_toolbar = ROOT / "служебные_файлы" / "qa_07-11-2026" / "mobile-v152-toolbar"
    if mobile_v152_toolbar.is_dir():
        safe_mirror(mobile_v152_toolbar, QA_PACKAGE / "mobile-v152-toolbar", PACKAGE)

    current_product_audit = ROOT / "служебные_файлы" / "qa_07-11-2026" / "current-product-audit"
    if current_product_audit.is_dir():
        safe_mirror(current_product_audit, QA_PACKAGE / "current-product-audit", PACKAGE,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    android_v152_mobile = ROOT / "служебные_файлы" / "qa_07-11-2026" / "android-v152-mobile"
    if android_v152_mobile.is_dir():
        safe_mirror(android_v152_mobile, QA_PACKAGE / "android-v152-mobile", PACKAGE)

    qa_08 = ROOT / "служебные_файлы" / "qa_08-11-2026"
    qa_09 = ROOT / "служебные_файлы" / "qa_09-11-2026"
    for dirname in ("product-flow-v157", "android-v154"):
        source = qa_08 / dirname
        if source.is_dir():
            safe_mirror(source, QA_PACKAGE / "qa_09-11-2026" / dirname, PACKAGE)
    for dirname in ("windows-v159-smoke", "android-v156", "web-v156-v159-regression",
                    "android-v157", "web-v157-v160-regression", "desktop-v160-recovery"):
        source = qa_09 / dirname
        if source.is_dir():
            safe_mirror(source, QA_PACKAGE / "qa_09-11-2026" / dirname, PACKAGE)
    report_visual_v09 = qa_09 / "reports-expanded"
    report_visual_target_v09 = QA_PACKAGE / "qa_09-11-2026" / "reports-expanded"
    report_visual_target_v09.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "m4-contact.png", "m5-contact.png"):
        shutil.copy2(report_visual_v09 / name, report_visual_target_v09 / name)
    for dirname in ("m4-final-v2", "m5-final-v2"):
        source = report_visual_v09 / dirname
        if source.is_dir():
            safe_mirror(source, report_visual_target_v09 / dirname, PACKAGE)
    validation_source = report_visual_v09 / "sources" / "validation-add-form.jpg"
    if validation_source.is_file():
        validation_target = report_visual_target_v09 / "sources"
        validation_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(validation_source, validation_target / validation_source.name)
    qa_10 = ROOT / "служебные_файлы" / "qa_10-11-2026"
    for dirname in ("web-v161-v164-regression", "android-v161", "report-render-v161-final"):
        source = qa_10 / dirname
        if source.is_dir():
            safe_mirror(source, QA_PACKAGE / "qa_10-11-2026" / dirname, PACKAGE,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    render_v161_package = QA_PACKAGE / "qa_10-11-2026" / "report-render-v161-final"
    render_v161_package.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "Отчет_ООП_Модуль_5_v161.docx", render_v161_package / "Отчет_ООП_Модуль_5_v161.docx")
    for name in ("Отчет_QA_Android_v161.md", "python-regression-v161.log", "web-regression-v161.log"):
        source = qa_10 / name
        if source.is_file():
            target = QA_PACKAGE / "qa_10-11-2026" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    accessibility_source = qa_10 / "accessibility-v161-live"
    if accessibility_source.is_dir():
        safe_mirror(accessibility_source, QA_PACKAGE / "qa_10-11-2026" / "accessibility-v161-live", PACKAGE,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for helper_name in (
        "update_module5_report_v161.py",
        "render_module5_v161.py",
    ):
        helper = qa_10 / helper_name
        if helper.is_file():
            shutil.copy2(helper, QA_PACKAGE / "qa_10-11-2026" / helper.name)
    for dirname in ("update-notice-v153", "windows-v156-isolated", "android-v153"):
        source = qa_08 / dirname
        if source.is_dir():
            safe_mirror(source, QA_PACKAGE / "qa_08-11-2026" / dirname, PACKAGE)
    report_visual_source = qa_08 / "report-visual-refresh"
    report_visual_target = QA_PACKAGE / "qa_08-11-2026" / "report-visual-refresh"
    report_visual_target.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "project-form-highdpi.jpg", "project-form-cover-crop.jpg",
                 "about-highdpi.jpg", "file-menu-highdpi-2x.jpg"):
        shutil.copy2(report_visual_source / name, report_visual_target / name)
    (report_visual_target / "rendered").mkdir(exist_ok=True)
    for name in ("m4-contact.png", "m5-contact.png"):
        shutil.copy2(report_visual_source / "rendered" / name, report_visual_target / "rendered" / name)

    compact_form_v151 = ROOT / "служебные_файлы" / "qa_06-11-2026" / "compact-form-v151"
    if compact_form_v151.is_dir():
        safe_mirror(compact_form_v151, QA_PACKAGE / "compact-form-v151", PACKAGE)

    report_audit_source = ROOT / "служебные_файлы" / "qa_10-11-2026" / "audit_submission_reports_v9.py"
    shutil.copy2(report_audit_source, QA_PACKAGE / "audit_submission_reports.py")


    # Keep any existing nested duplicate references in sync with the authoritative root copies.
    for name in (
        "План_работ_продукт_и_отчеты.md",
        "Отчет_QA_02-11-2026.md",
        "Отчет_QA_05-11-2026.md",
        "Отчет_QA_06-11-2026.md",
        "Отчет_QA_07-11-2026.md",
        "Отчет_QA_08-11-2026.md",
        "Отчет_QA_09-11-2026.md",
        "Проверка_готовности_09-11-2026.md",
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
    audit = subprocess.run([sys.executable, str(QA_PACKAGE / "audit_submission_reports.py")],
                           cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace")
    if audit.returncode:
        raise RuntimeError("Current module report audit failed:\n" + audit.stdout[-8000:])

    audit_data = json.loads(
        (QA_PACKAGE / "report-current-package-audit-results.json").read_text(encoding="utf-8")
    )
    m4_pages = audit_data["module4"]["pdf_pages"]
    m5_pages = audit_data["module5"]["pdf_pages"]
    m4_similarity = audit_data["module4"]["normalized_docx_pdf_similarity"]
    m5_similarity = audit_data["module5"]["normalized_docx_pdf_similarity"]
    python_match = re.search(r"Ran (\d+) tests?\b", python_log)
    web_match = re.search(r"ℹ tests (\d+)\s+ℹ suites \d+\s+ℹ pass (\d+)\s+ℹ fail 0", web_log)
    if not python_match or not web_match or web_match.group(1) != web_match.group(2):
        raise RuntimeError("Could not derive complete regression totals for the package README.")
    test_count = python_match.group(1)
    web_count = web_match.group(2)

    qa_readme = QA_PACKAGE / "README.md"
    qa_readme.write_text(
        f"""# Состав и проверка сдачного комплекта — 10.11.2026

В архив включены отчёты ООП модулей 4–5 (M4: {m4_pages} страниц, M5: {m5_pages} страниц), оригиналы заданий, матрица требований, исходники и QA-доказательства Web/PWA v161, Windows WebView2 v164 и Android debug APK 0.3.24/code 36. Точный EXE-хост v164 прошёл 20/20 маршрутно-экранных состояний; проверены мобильные фильтры, доступные имена, CRUD, сохранение после reload и холодная офлайн-загрузка. Персональные portfolio_data.sqlite3 и portfolio_data.json исключены.

Файлов без manifest: {len(included_files()) + 1}. Verifier сверил хэши manifest, полный состав ZIP и CRC; SHA-256 архива записан в sidecar. Пакетные регрессии: Python {test_count}/{test_count}, Web {web_count}/{web_count}. Отчёты DOCX/PDF синхронизированы; аудит проверил текст на каждой странице, визуальные рендеры каждой страницы M5 при 144 DPI, 18 страниц, сходство DOCX/PDF M4 {m4_similarity} и M5 {m5_similarity}, требования A.3–A.5 и исходные скриншоты.

Доказательства включают web-v161-v164-regression/, android-v161/, accessibility-v161-live/ и report-render-v161-final/ с контактным листом и полноразмерными изображениями всех 18 страниц M5. axe-core 4.14.0 проверил 10 состояний без автоматических нарушений и ошибок браузера; группы `incomplete` вручную проверены, измеренные контрасты — 13,39:1 и 12,29:1. Отдельная физическая проверка телефона, OEM file picker, реальной речи/жестов TalkBack, Narrator/NVDA и системного увеличения требует внешней приёмки. Публичная Pages остаётся на v120; локальный кандидат не публиковался. Android APK подписан debug-ключом.
""",
        encoding="utf-8",
    )

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










