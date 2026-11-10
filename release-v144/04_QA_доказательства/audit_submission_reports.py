from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.oxml.ns import qn
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"
REPORTS = PACKAGE / "01_Отчёты"
QA = PACKAGE / "04_QA_доказательства"
ANDROID_APK = PACKAGE / "02_Приложение" / "mobile" / "folio-android-debug.apk"
ANDROID_PHONE_ZIP = PACKAGE / "02_Приложение" / "mobile" / "folio-android-debug-for-phone.zip"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def embedded_images(path: Path) -> list[dict]:
    doc = Document(path)
    out = []
    for shape in doc.inline_shapes:
        blip = shape._inline.graphic.graphicData.pic.blipFill.blip
        rid = blip.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        )
        blob = doc.part.related_parts[rid].blob
        out.append({
            "dimensions_px": list(Image.open(BytesIO(blob)).size),
            "sha256": sha_bytes(blob),
        })
    return out


def inspect(module: int) -> dict:
    doc = REPORTS / f"Отчёт_ООП_Модуль_{module}.docx"
    pdf = REPORTS / f"Отчёт_ООП_Модуль_{module}.pdf"
    text = doc_text(doc)
    pages = [page.extract_text() or "" for page in PdfReader(str(pdf)).pages]
    pdf_text = "\n".join(pages)
    images = embedded_images(doc)
    return {
        "docx": doc.name,
        "pdf": pdf.name,
        "docx_sha256": sha(doc),
        "pdf_sha256": sha(pdf),
        "docx_chars": len(text),
        "pdf_pages": len(pages),
        "all_pdf_pages_have_text": bool(pages)
            and all(bool(re.sub(r"\s", "", page)) for page in pages),
        "normalized_docx_pdf_similarity": round(
            SequenceMatcher(None, norm(text), norm(pdf_text)).ratio(), 6
        ),
        "inline_images": len(images),
        "embedded_image_dimensions_px": [item["dimensions_px"] for item in images],
        "embedded_image_sha256": [item["sha256"] for item in images],
        "docx_text": text,
    }


def render_folder_check(folder: Path, expected_pages: int) -> bool:
    pages = sorted(folder.glob("page-*.png"))
    if len(pages) != expected_pages:
        return False
    try:
        for path in pages:
            with Image.open(path) as image:
                if image.width < 1200 or image.height < 1500:
                    return False
                image.verify()
    except Exception:
        return False
    return True


m4 = inspect(4)
m5 = inspect(5)
validation_source = (
    QA / "qa_09-11-2026" / "reports-expanded" / "sources" / "validation-add-form.jpg"
)
validation_hash = sha(validation_source) if validation_source.is_file() else ""
reports_visual_m4 = QA / "qa_09-11-2026" / "reports-expanded"
reports_visual_m5 = QA / "qa_10-11-2026" / "report-render-v161-final"
file_menu_source = QA / "qa_08-11-2026" / "report-visual-refresh" / "file-menu-highdpi-2x.jpg"
file_menu_source_hash = sha(file_menu_source) if file_menu_source.is_file() else ""

python_log = (QA / "python-regression-package.log").read_text(
    encoding="utf-8", errors="replace"
)
web_log = (QA / "web-regression-package.log").read_text(
    encoding="utf-8", errors="replace"
)
web_v161_path = QA / "qa_10-11-2026" / "web-v161-v164-regression" / "result.json"
web_v161 = json.loads(web_v161_path.read_text(encoding="utf-8")) if web_v161_path.is_file() else {}
web_v161_matrix = web_v161.get("route_matrix", [])
current_report_screenshot = QA / "qa_10-11-2026" / "web-v161-v164-regression" / "projects-1440x900.png"
current_report_screenshot_hash = sha(current_report_screenshot) if current_report_screenshot.is_file() else ""
android_v161_dir = QA / "qa_10-11-2026" / "android-v161"
android_report_path = QA / "qa_10-11-2026" / "Отчет_QA_Android_v161.md"
android_report = android_report_path.read_text(encoding="utf-8") if android_report_path.is_file() else ""
android_apk_hash = re.search(r"folio-android-debug[.]apk.*?SHA-256 `?([0-9a-f]{64})", android_report, re.I)
android_phone_zip_hash = re.search(
    r"folio-android-debug-for-phone[.]zip.*?SHA-256 `?([0-9a-f]{64})", android_report, re.I
)
render_v161_path = QA / "qa_10-11-2026" / "report-render-v161-final" / "render.json"
render_v161 = json.loads(render_v161_path.read_text(encoding="utf-8")) if render_v161_path.is_file() else {}
axe_v161_path = QA / "qa_10-11-2026" / "accessibility-v161-live" / "axe-core-4.14.0-results.json"
axe_v161 = json.loads(axe_v161_path.read_text(encoding="utf-8")) if axe_v161_path.is_file() else {}
accessibility_v161_path = QA / "qa_10-11-2026" / "accessibility-v161-live" / "result.json"
accessibility_v161 = json.loads(accessibility_v161_path.read_text(encoding="utf-8")) if accessibility_v161_path.is_file() else {}
contrast_review_v161_path = QA / "qa_10-11-2026" / "accessibility-v161-live" / "contrast-review-v161.md"
contrast_review_v161 = contrast_review_v161_path.read_text(encoding="utf-8", errors="replace") if contrast_review_v161_path.is_file() else ""
recovery_v160_path = QA / "qa_09-11-2026" / "desktop-v160-recovery" / "result.json"
recovery_v160 = json.loads(recovery_v160_path.read_text(encoding="utf-8")) if recovery_v160_path.is_file() else {}

checks = {
    "module4_has_large_project_form": [762, 792] in m4["embedded_image_dimensions_px"],
    "module4_has_lower_form_crop": m4["embedded_image_dimensions_px"].count([762, 792]) >= 2,
    "module4_has_large_about_window": [396, 352] in m4["embedded_image_dimensions_px"],
    "module5_file_menu_matches_highdpi_2x_source": (
        bool(file_menu_source_hash) and file_menu_source_hash in m5["embedded_image_sha256"]
    ),
    "module5_current_v161_v164_screenshot_is_embedded": (
        bool(current_report_screenshot_hash)
        and current_report_screenshot_hash in m5["embedded_image_sha256"]
        and "Web/PWA v161" in m5["docx_text"]
        and "Windows WebView2 v164" in m5["docx_text"]
    ),
    "module4_pdf_12_pages": m4["pdf_pages"] == 12,
    "module5_pdf_18_pages": m5["pdf_pages"] == 18,
    "module4_all_pdf_pages_have_text": m4["all_pdf_pages_have_text"],
    "module5_all_pdf_pages_have_text": m5["all_pdf_pages_have_text"],
    "module4_docx_pdf_similarity_ge_0_98": m4["normalized_docx_pdf_similarity"] >= 0.98,
    "module5_docx_pdf_similarity_ge_0_98": m5["normalized_docx_pdf_similarity"] >= 0.98,
    "module4_m5_docx_pdf_candidate_sync": all(
        sha(
            ROOT / (f"Отчет_ООП_Модуль_{number}_v161.{extension}" if number == 5
                   else f"Отчет_ООП_Модуль_{number}.{extension}")
        ) == sha(REPORTS / f"Отчёт_ООП_Модуль_{number}.{extension}")
        for number in (4, 5)
        for extension in ("docx", "pdf")
    ),
    "module5_has_a3_a4_a5_evidence_sections": all(
        heading in m5["docx_text"]
        for heading in (
            "А.3 Поиск в таблице настольной версии",
            "А.4 Проверка обязательных полей",
            "А.5 Подтверждение удаления",
        )
    ),
    "module5_validation_source_is_present": bool(validation_hash),
    "module5_full_validation_screenshot_matches_source": (
        bool(validation_hash) and validation_hash in m5["embedded_image_sha256"]
    ),
    "module5_full_validation_screenshot_dimensions": [1282, 892]
        in m5["embedded_image_dimensions_px"],
    "m4_contact_sheet_present": (reports_visual_m4 / "m4-contact.png").is_file(),
    "m5_contact_sheet_present": (reports_visual_m5 / "contact-sheet.png").is_file(),
    "m4_all_final_page_renders_present": render_folder_check(
        reports_visual_m4 / "m4-final-v2", 12
    ),
    "m5_all_final_page_renders_present": render_folder_check(
        reports_visual_m5, 18
    ),
    "windows_desktop_screenshot_present": (
        QA / "qa_09-11-2026" / "product-flow-v157" / "dashboard-1440x900.png"
    ).is_file(),
    "android_after_update_screenshot_present": (
        QA / "qa_09-11-2026" / "android-v154" / "dashboard-after-update.png"
    ).is_file(),
    "windows_v159_dashboard_and_showcase_screenshots_present": all(
        (QA / "qa_09-11-2026" / "windows-v159-smoke" / name).is_file()
        for name in ("dashboard.jpg", "showcase.jpg")
    ),
    "android_v156_after_update_screenshot_present": (
        QA / "qa_09-11-2026" / "android-v156" / "after-update.png"
    ).is_file(),
    "android_v161_screenshots_and_version_present": (
        "0.3.24" in android_report
        and "versionCode 36" in android_report
        and all((android_v161_dir / name).is_file()
                for name in ("after-update.png", "updated-dashboard.png", "offline-cold-launch.png",
                             "uiautomator.xml"))
    ),
    "android_v161_offline_state_documented": "Active default network: none" in android_report,
    "android_v161_apk_matches_reported_hash": (
        android_apk_hash is not None
        and ANDROID_APK.is_file()
        and sha(ANDROID_APK).lower() == android_apk_hash.group(1).lower()
    ),
    "android_v161_phone_zip_matches_reported_hash": (
        android_phone_zip_hash is not None
        and ANDROID_PHONE_ZIP.is_file()
        and sha(ANDROID_PHONE_ZIP).lower() == android_phone_zip_hash.group(1).lower()
    ),
    "desktop_v160_recovery_synthetic_flow_passed": (
        recovery_v160.get("passed") is True
        and recovery_v160.get("recoveredProjectCards") == 4
        and recovery_v160.get("syntheticMarkerVisible") is True
        and recovery_v160.get("originalSnapshotRestored") is True
        and (QA / "qa_09-11-2026" / "desktop-v160-recovery" / "recovered-projects-v160-1440x900.png").is_file()
    ),
    "web_v161_via_v164_host_route_matrix_20_passed": (
        web_v161.get("http_status") == 200
        and len(web_v161_matrix) == 20
        and all(
            row.get("noHorizontalOverflow")
            and not row.get("touchTargetsBelow44")
            and row.get("brokenProjectImages") == 0
            for row in web_v161_matrix
        )
    ),
    "web_v161_via_v164_host_browser_errors_zero": (
        bool(web_v161) and web_v161.get("browser_errors") == []
    ),
    "web_v161_via_v164_host_offline_cold_reload_passed": (
        web_v161.get("offline_cold_reload", {}).get("controller") is True
        and web_v161.get("offline_cold_reload", {}).get("online") is False
        and web_v161.get("offline_cold_reload", {}).get("projectCount") == 3
        and web_v161.get("offline_cold_reload", {}).get("brokenImages") == 0
    ),
    "web_v161_via_v164_host_crud_flow_passed": (
        web_v161.get("crud_flow", {}).get("wizard_visible_on_mobile") is True
        and web_v161.get("crud_flow", {}).get("create_project_persisted_after_reload") is True
        and web_v161.get("crud_flow", {}).get("edit_project_visible_in_card") is True
        and web_v161.get("crud_flow", {}).get("undo_delete_restored_project") is True
        and web_v161.get("crud_flow", {}).get("recoverable_delete_expired_and_restored_demo_count") == 3
    ),
    "web_v161_mobile_readability_min_10px": all(
        row.get("mobileReadability") is None
        or row.get("mobileReadability", {}).get("smallestFontPx", 0) >= 10
        for row in web_v161_matrix
        if row.get("viewport", [1000])[0] <= 390
    ),
    "web_v161_mobile_disclosures_hidden_and_accessibly_named": (
        web_v161.get("mobile_disclosures_closed", {}).get("filterOpen") is False
        and web_v161.get("mobile_disclosures_closed", {}).get("savedViewsOpen") is False
        and all(
            body.get("display") == "none"
            and body.get("clientRects") == 0
            and body.get("visibleControls") == 0
            for body in (
                web_v161.get("mobile_disclosures_closed", {}).get("filterBody", {}),
                web_v161.get("mobile_disclosures_closed", {}).get("savedViewsBody", {}),
            )
        )
        and all(value == 1 for value in web_v161.get("mobile_disclosures_open_controls", {}).get(
            "filter_controls_by_accessible_name", {}
        ).values())
        and all(value == 1 for value in web_v161.get("mobile_disclosures_open_controls", {}).get(
            "saved_view_controls_by_accessible_name", {}
        ).values())
    ),
    "python_regression_97_passed": bool(
        re.search(r"Ran 97 tests?\b", python_log) and re.search(r"\bOK\b", python_log)
    ),
    "web_regression_85_passed": bool(
        re.search(r"ℹ tests 85\s+ℹ suites \d+\s+ℹ pass 85\s+ℹ fail 0", web_log)
    ),
    "module5_render_v161_metadata_matches_pdf_and_docx": (
        render_v161.get("pdf_pages") == 18
        and render_v161.get("rendered_png_pages") == 18
        and render_v161.get("source_docx_sha256") == m5["docx_sha256"]
        and render_v161.get("rendered_pdf_sha256") == m5["pdf_sha256"]
        and render_v161.get("docx_pdf_text_similarity", 0) >= 0.98
    ),
    "axe_v161_10_states_zero_violations_and_browser_errors": (
        axe_v161.get("axe_version") == "4.14.0"
        and len(axe_v161.get("states", [])) == 10
        and axe_v161.get("violation_count") == 0
        and axe_v161.get("all_scans_have_zero_violations") is True
        and axe_v161.get("browser_errors_zero") is True
    ),
    "axe_v161_incomplete_contrast_groups_have_manual_review": (
        axe_v161.get("incomplete_count", 0) > 0
        and "13,39:1" in contrast_review_v161
        and "12,29:1" in contrast_review_v161
    ),
    "accessibility_v161_keyboard_snapshot_passed": (
        accessibility_v161.get("all_checks_passed") is True
        and accessibility_v161.get("browser_errors") == []
    ),
}

result = {
    "date": "2026-11-10",
    "scope": (
        "local-first Folio: Web/PWA v161 through Windows WebView2 v164 local host, "
        "Android debug 0.3.24/code 36 emulator update; final OOP modules 4 and 5 reports"
    ),
    "module4": {key: value for key, value in m4.items() if key != "docx_text"},
    "module5": {key: value for key, value in m5.items() if key != "docx_text"},
    "module5_validation_source_sha256": validation_hash,
    "module5_file_menu_2x_source_sha256": file_menu_source_hash,
    "module5_render_v161": render_v161,
    "accessibility_v161": {
        "axe_version": axe_v161.get("axe_version"),
        "states": len(axe_v161.get("states", [])),
        "violations": axe_v161.get("violation_count"),
        "incomplete": axe_v161.get("incomplete_count"),
        "browser_errors_zero": axe_v161.get("browser_errors_zero"),
        "keyboard_snapshot_passed": accessibility_v161.get("all_checks_passed"),
    },
    "web_v161_via_v164_host_summary": {
        "url": web_v161.get("url"),
        "matrix_rows": len(web_v161_matrix),
        "offline_cold_reload": web_v161.get("offline_cold_reload"),
        "crud_flow": web_v161.get("crud_flow"),
        "mobile_disclosures_closed": web_v161.get("mobile_disclosures_closed"),
        "mobile_disclosures_open_controls": web_v161.get("mobile_disclosures_open_controls"),
        "screenshot_count": len(web_v161.get("screenshots", [])),
    },
    "android_v161_report": android_report,
    "desktop_v160_recovery": recovery_v160,
    "module5_current_screenshot_sha256": current_report_screenshot_hash,
    "checks": checks,
    "all_checks_passed": all(checks.values()),
}
out = QA / "report-current-package-audit-results.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result["all_checks_passed"]:
    raise SystemExit("Current report/package audit failed.")
