from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"
FIXTURE = {
    "schema_version": 1,
    "title": "QA — перенос JSON",
    "next_id": 42,
    "developer": {"full_name": "QA Автор", "specialization": "Проверка переноса"},
    "projects": [{
        "id": 41,
        "type": "Веб-приложение",
        "title": "QA interop case",
        "description": "Синтетический кейс для проверки переноса между desktop и web.",
        "created_at": "2026-11-01",
        "status": "Завершён",
        "technologies": [
            {"name": "SQLite", "category": "СУБД", "version": "3.46"},
            {"name": "Python", "category": "Язык программирования", "version": "3.13"},
        ],
        "repository_url": "",
        "backend_stack": "Flask",
        "demo_url": "",
        "role": "QA",
        "outcome": "Проверен круговой перенос.",
        "context": "Тестовые данные без пользовательской информации.",
        "solution": "Импорт, редактирование и повторный экспорт.",
        "process": "Синтетический сценарий в чистом профиле.",
        "metrics": "Данные категории и версии должны сохраниться.",
        "tags": ["QA"],
        "featured": True,
        "cover_image_data": "data:image/png;base64,AA==",
        "gallery_images": [{"image_data": "data:image/png;base64,AA==", "alt": "Синтетическая картинка", "position": "20% 80%"}],
    }],
}


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True, service_workers="allow")
        page = context.new_page()
        page.set_default_timeout(10_000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        response = page.goto(URL, wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise AssertionError("PWA did not load successfully.")
        page.wait_for_timeout(1200)
        page.locator("#import-file").set_input_files({
            "name": "synthetic-interop-fixture.json",
            "mimeType": "application/json",
            "buffer": json.dumps(FIXTURE, ensure_ascii=False).encode("utf-8"),
        })
        page.locator("#import-dialog").wait_for(state="visible")
        with page.expect_download(timeout=10_000):
            page.locator("#import-replace").click()
        page.locator('[data-view="projects"]:visible').first.click()
        if page.locator('[data-detail="41"]').count() != 1:
            raise AssertionError("The imported QA project is not present exactly once.")
        page.locator('[data-detail="41"]').click()
        detail_text = page.locator('#detail-content').inner_text()
        page.locator('[data-edit="41"]').click()
        page.wait_for_function("document.querySelector('#project-dialog-title')?.textContent.includes('Редактировать')")
        tech_input = page.locator('#project-form [name="technologies"]')
        form_title = page.locator('#project-form [name="title"]').input_value()
        if tech_input.input_value() != "SQLite, Python":
            raise AssertionError(f"Imported project/form state mismatch: dialog={page.locator('#project-dialog-title').inner_text()!r}; title={form_title!r}; technologies={tech_input.input_value()!r}; detail_has_title={'QA interop case' in detail_text}")
        page.screenshot(path=str(OUT / "interop-ui-edit-v85-mobile.png"))
        page.locator('#project-form button[type="submit"]').click()
        page.locator("#project-dialog").wait_for(state="hidden")
        page.locator('[data-view="settings"]:visible').click()
        export_button = page.locator('[data-action="export-json"]')
        export_button.wait_for(state="visible", timeout=10_000)
        with page.expect_download(timeout=10_000) as download_info:
            export_button.click()
        download = download_info.value
        export_path = OUT / "interop-ui-export-v85.json"
        download.save_as(export_path)
        exported = json.loads(export_path.read_text(encoding="utf-8"))
        technologies = exported["projects"][0]["technologies"]
        expected = FIXTURE["projects"][0]["technologies"]
        if technologies != expected:
            raise AssertionError(f"Technology metadata changed in UI round-trip: {technologies!r}")
        if exported["projects"][0]["gallery_images"] != FIXTURE["projects"][0]["gallery_images"]:
            raise AssertionError("Gallery data changed in UI round-trip.")
        if errors:
            raise AssertionError(f"Browser errors: {errors}")

        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "result": "PASS",
            "route": "PWA UI import -> edit unchanged technologies -> UI JSON export",
            "synthetic_fixture_only": True,
            "checks": {
                "replace_import_completed": True,
                "project_edit_form_loaded": True,
                "project_saved": True,
                "technology_categories_and_versions_preserved": True,
                "gallery_alt_and_crop_preserved": True,
                "page_and_console_errors": errors,
            },
            "export": export_path.name,
            "screenshot": "interop-ui-edit-v85-mobile.png",
            "isolated_context": True,
        }
        (OUT / "interop-ui-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        browser.close()
        print("PASS: PWA UI import/edit/export preserves technology metadata and gallery; evidence saved.")


if __name__ == "__main__":
    main()
