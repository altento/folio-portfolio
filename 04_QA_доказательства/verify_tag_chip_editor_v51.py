from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

QA = Path(__file__).resolve().parent
WEB = QA.parent / "02_Приложение" / "web"
TEMP = Path(tempfile.mkdtemp(prefix="folio-v51-tags-"))
SITE = TEMP / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *_args):
        pass


async def main():
    shutil.copytree(WEB, SITE)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    result = {"version": "v51-tag-chip-editor", "errors": [], "tags": {}, "backup": {}, "responsive": {}, "draft": {}}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            assert response and response.status == 200
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            form = page.locator("#project-form")
            entry = page.locator("#case-tag-entry")

            await entry.fill("React")
            await entry.press("Enter")
            await page.wait_for_function("document.querySelector('#case-tags-data').value==='React'")
            await entry.fill("react, CRM, frontend")
            await page.locator("#case-tag-add").click()
            await page.wait_for_function("document.querySelector('#case-tags-data').value==='React, CRM, frontend'")
            result["tags"]["deduplicatesCaseInsensitively"] = await page.locator("#case-tags-count").inner_text() == "3 из 20"
            result["tags"]["suggestionsAvailable"] = await page.locator("#case-tag-suggestions option").count() > 0
            assert result["tags"]["deduplicatesCaseInsensitively"] and result["tags"]["suggestionsAvailable"]

            await entry.fill("x" * 33)
            await page.locator("#case-tag-add").click()
            result["tags"]["invalidLengthPreservesExisting"] = (
                await entry.get_attribute("aria-invalid") == "true"
                and await page.locator("#case-tags-data").input_value() == "React, CRM, frontend"
            )
            assert result["tags"]["invalidLengthPreservesExisting"]
            await page.locator('[data-case-tag-remove="1"]').click()
            result["tags"]["removeRestoresEntryFocus"] = await entry.evaluate("el=>document.activeElement===el")
            await entry.fill("CRM")
            await entry.press("Enter")
            assert result["tags"]["removeRestoresEntryFocus"]
            assert await page.locator("#case-tags-data").input_value() == "React, frontend, CRM"

            tag_field = page.locator(".field:has(.case-tag-editor)")
            box = await tag_field.bounding_box()
            await page.screenshot(path=str(QA / "web-tags-v51-desktop-1440x900.png"), clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]})
            result["responsive"]["desktopDocumentWidth"] = await page.evaluate("document.documentElement.scrollWidth")
            for width, height, filename in [(390, 844, "web-tags-v51-mobile-390x844.png"), (320, 568, "web-tags-v51-mobile-320x568.png")]:
                await page.set_viewport_size({"width": width, "height": height})
                await page.evaluate("""()=>{const dialog=document.querySelector('#project-dialog'),field=document.querySelector('.field:has(.case-tag-editor)');dialog.scrollTop=Math.max(0,field.offsetTop-70)}""")
                result["responsive"][f"{width}Geometry"] = await page.evaluate("""()=>{const a=document.querySelector('.field:has(.case-tag-editor)').getBoundingClientRect(),b=document.querySelector('.dialog-actions').getBoundingClientRect(),h=document.querySelector('#case-tags-help').getBoundingClientRect();return {field:[Math.round(a.top),Math.round(a.bottom)],actions:[Math.round(b.top),Math.round(b.bottom)],help:[Math.round(h.top),Math.round(h.bottom)]}}""")
                box = await tag_field.bounding_box()
                await page.screenshot(path=str(QA / filename), clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]})
                result["responsive"][str(width)] = await page.evaluate("({doc:document.documentElement.scrollWidth,inner:innerWidth,entry:document.querySelector('#case-tag-entry').getBoundingClientRect().width,button:document.querySelector('#case-tag-add').getBoundingClientRect().width})")
                geometry = result["responsive"][f"{width}Geometry"]
                assert result["responsive"][str(width)]["doc"] == width, result["responsive"][str(width)]
                assert result["responsive"][str(width)]["entry"] > 0 and result["responsive"][str(width)]["button"] >= 44
                assert geometry["help"][1] <= geometry["actions"][0], geometry

            await form.locator('[name="title"]').fill("QA: редактор тегов v51")
            await form.locator('[name="description"]').fill("Сохранение и редактирование тегов без изменения JSON-схемы.")
            await form.locator('[name="created_at"]').fill("2026-10-30")
            await form.locator('[type="submit"]').click()
            await page.get_by_text("QA: редактор тегов v51", exact=True).first.wait_for(timeout=10000)
            card = page.locator(".project-card").filter(has_text="QA: редактор тегов v51")
            await card.locator("[data-detail]").click()
            await page.locator("#detail-dialog [data-edit]").click()
            result["tags"]["savedAndEditable"] = await page.locator("#case-tags-data").input_value() == "React, frontend, CRM"
            assert result["tags"]["savedAndEditable"]
            await page.locator("#project-dialog [data-close-dialog]").last.click()

            await page.set_viewport_size({"width": 1440, "height": 900})
            await page.locator("#project-dialog").wait_for(state="hidden", timeout=5000)
            await page.wait_for_function("innerWidth===1440")
            await page.locator('.sidebar [data-view="settings"]:visible').click()
            backup_path = TEMP / "folio-backup-v51.json"
            async with page.expect_download() as download_info:
                await page.locator('[data-action="export-json"]:visible').click()
            await (await download_info.value).save_as(backup_path)
            portable = json.loads(backup_path.read_text(encoding="utf-8"))
            portable_case = next(project for project in portable["projects"] if project["title"] == "QA: редактор тегов v51")
            result["backup"]["portableTags"] = portable_case["tags"]
            assert portable_case["tags"] == ["React", "frontend", "CRM"]

            import_context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            import_page = await import_context.new_page()
            import_page.on("pageerror", lambda error: result["errors"].append(str(error)))
            import_page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            await import_page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            await import_page.locator('.sidebar [data-view="settings"]:visible').click()
            await import_page.locator("#import-file").set_input_files(str(backup_path))
            await import_page.locator("#import-dialog").wait_for(state="visible", timeout=10000)
            result["backup"]["previewShown"] = "проект" in (await import_page.locator("#import-summary").inner_text()).lower()
            assert result["backup"]["previewShown"]
            async with import_page.expect_download() as before_import_info:
                await import_page.locator("#import-replace").click()
            await (await before_import_info.value).save_as(TEMP / "folio-before-import-v51.json")
            await import_page.locator("#import-dialog").wait_for(state="hidden", timeout=10000)
            await import_page.locator('nav [data-view="projects"]:visible').click()
            imported_card = import_page.locator(".project-card").filter(has_text="QA: редактор тегов v51")
            await imported_card.locator("[data-detail]").click()
            await import_page.locator("#detail-dialog [data-edit]").click()
            await import_page.wait_for_function("document.querySelector('#project-form [name=title]').value==='QA: редактор тегов v51'", timeout=5000)
            result["backup"]["importedEditorTitle"] = await import_page.locator('#project-form [name="title"]').input_value()
            result["backup"]["importedInputValue"] = await import_page.locator("#case-tags-data").input_value()
            result["backup"]["importedTagChips"] = await import_page.locator("#case-tag-list").inner_text()
            result["backup"]["restoredTagsEditable"] = result["backup"]["importedInputValue"] == "React, frontend, CRM"
            result["backup"]["replacementBackupDownloaded"] = (TEMP / "folio-before-import-v51.json").is_file()
            assert result["backup"]["restoredTagsEditable"] and result["backup"]["replacementBackupDownloaded"], result["backup"]
            await import_context.close()

            await page.locator('[data-action="new-project"]:visible').first.click()
            await page.locator("#case-tag-entry").fill("черновой тег")
            await page.wait_for_timeout(500)
            await page.wait_for_function("document.querySelector('#project-draft-status').textContent.includes('Черновик сохранён')", timeout=3000)
            result["draft"]["savedBeforeReload"] = True
            await page.reload(wait_until="networkidle")
            page.once("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            await page.locator("#case-tag-entry").wait_for(state="visible")
            result["draft"]["entryRestored"] = await page.locator("#case-tag-entry").input_value() == "черновой тег"
            assert result["draft"]["savedBeforeReload"] and result["draft"]["entryRestored"]
            assert not result["errors"], result["errors"]
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()

    (QA / "web-tags-v51-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
