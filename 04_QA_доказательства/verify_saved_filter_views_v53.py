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
TEMP = Path(tempfile.mkdtemp(prefix="folio-v53-saved-filters-"))
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
    result = {"version": "v53-saved-filter-views", "checks": {}, "errors": []}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            assert response and response.status == 200
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v53-saved-filter-views')", timeout=15000)
            result["checks"]["serviceWorkerUsesV53Cache"] = await page.evaluate("async()=>{const keys=await caches.keys();return keys.includes('folio-shell-v53-saved-filter-views')&&!keys.some(key=>key==='folio-shell-v52-delete-undo')}")
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator("#search-input").fill("CRM")
            await page.locator("#sort-projects").select_option("newest")
            expected_count = await page.locator(".project-card").count()
            assert expected_count == 1, expected_count
            await page.locator('[data-action="save-filter-view"]').click()
            await page.locator("#saved-filter-dialog").wait_for(state="visible")
            await page.locator("#saved-filter-name").fill("CRM недавние")
            await page.screenshot(path=str(QA / "web-saved-filters-v53-dialog-1440x900.png"))
            await page.locator('#saved-filter-form button[type="submit"]').click()
            result["checks"]["saveKeepsSearchAndSort"] = await page.locator("#search-input").input_value() == "CRM" and await page.locator("#sort-projects").input_value() == "newest"
            result["checks"]["savedViewSelectedAndCounted"] = await page.locator("#saved-filter-view").input_value() != "" and await page.locator(".saved-view-limit").inner_text() == "1/12"

            await page.locator("#search-input").fill("Карта")
            await page.locator('[data-action="save-filter-view"]').click()
            await page.locator("#saved-filter-name").fill("crm недавние")
            await page.locator('#saved-filter-form button[type="submit"]').click()
            result["checks"]["duplicateNamesAreCaseInsensitive"] = "уже используется" in (await page.locator("#saved-filter-form-error").inner_text()).lower()
            await page.locator("#saved-filter-name").fill("Карта")
            await page.locator('#saved-filter-form button[type="submit"]').click()
            result["checks"]["secondViewSaved"] = await page.locator(".saved-view-limit").inner_text() == "2/12"
            await page.screenshot(path=str(QA / "web-saved-filters-v53-desktop-1440x900.png"), full_page=True)

            await page.locator("#search-input").fill("no-such-case")
            result["checks"]["manualChangesClearActiveSelection"] = await page.locator("#saved-filter-view").input_value() == ""
            await page.locator("#saved-filter-view").select_option(label="CRM недавние")
            result["checks"]["applyRestoresAllCriteria"] = await page.locator("#search-input").input_value() == "CRM" and await page.locator("#sort-projects").input_value() == "newest" and await page.locator(".project-card").count() == 1
            result["checks"]["activeViewCanBeRemoved"] = await page.locator('[data-action="delete-filter-view"]').is_enabled()

            await page.reload(wait_until="networkidle")
            await page.locator('nav [data-view="projects"]:visible').click()
            result["checks"]["savedViewPersistsAcrossReload"] = await page.locator("#saved-filter-view option").count() == 3
            await page.locator("#saved-filter-view").select_option(label="CRM недавние")
            result["checks"]["savedViewCanBeReappliedAfterReload"] = await page.locator("#search-input").input_value() == "CRM" and await page.locator("#sort-projects").input_value() == "newest"

            await page.set_viewport_size({"width": 390, "height": 844})
            result["checks"]["mobileNoHorizontalOverflow"] = await page.evaluate("document.documentElement.scrollWidth===innerWidth")
            bounds = await page.locator(".saved-views").evaluate("el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,scroll:el.scrollWidth,client:el.clientWidth}}")
            result["checks"]["mobileToolbarFits"] = bounds["scroll"] <= bounds["client"] and bounds["left"] >= 0 and bounds["right"] <= 390
            await page.locator("#toast-region .toast").wait_for(state="hidden", timeout=5000)
            await page.screenshot(path=str(QA / "web-saved-filters-v53-mobile-390x844.png"))
            await page.set_viewport_size({"width": 320, "height": 568})
            result["checks"]["smallMobileNoHorizontalOverflow"] = await page.evaluate("document.documentElement.scrollWidth===innerWidth")
            result["checks"]["smallSortLabelIsCompact"] = await page.locator("#sort-projects").evaluate("el=>el.selectedOptions[0].textContent==='Новые'")
            small_bounds = await page.locator(".saved-views").evaluate("el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,scroll:el.scrollWidth,client:el.clientWidth}}")
            result["checks"]["smallMobileToolbarFits"] = small_bounds["scroll"] <= small_bounds["client"] and small_bounds["left"] >= 0 and small_bounds["right"] <= 320
            await page.locator(".saved-views").scroll_into_view_if_needed()
            await page.evaluate("()=>{const r=document.querySelector('.saved-views').getBoundingClientRect(),visibleBottom=innerHeight-72;if(r.bottom>visibleBottom)window.scrollBy(0,r.bottom-visibleBottom+8)}")
            await page.screenshot(path=str(QA / "web-saved-filters-v53-mobile-320x568.png"))
            await page.set_viewport_size({"width": 390, "height": 844})

            await page.locator('[data-action="delete-filter-view"]').click()
            result["checks"]["deleteRemovesSelectedView"] = await page.locator("#saved-filter-view option").count() == 2 and await page.locator("#saved-filter-view").input_value() == ""
            await page.locator("#toast-region .toast .toast-action").click()
            result["checks"]["deletedViewCanBeRestored"] = await page.locator("#saved-filter-view option").count() == 3 and "восстановлена" in (await page.locator("#toast-region").inner_text()).lower()
            await page.locator("#saved-filter-view").select_option(label="CRM недавние")
            await page.locator('[data-action="delete-filter-view"]').click()
            await page.locator("#toast-region .toast").wait_for(state="visible")
            await page.locator("#toast-region .toast").wait_for(state="hidden", timeout=9000)
            await page.locator("#saved-filter-view").select_option(label="Карта")
            await page.locator('[data-action="delete-filter-view"]').click()
            stored = await page.evaluate("localStorage.getItem('folio-saved-filter-views-v1')")
            result["checks"]["deleteClearsDeviceOnlyPreference"] = stored == "[]" and await page.locator("#saved-filter-view option").count() == 1

            stale_view = [{"id": "stale-tag", "name": "Удалённый тег", "filters": {"query": "", "type": "Все типы", "status": "Все статусы", "tag": "Тег, которого больше нет", "sort": "featured", "featuredOnly": False}}]
            await page.evaluate("views=>localStorage.setItem('folio-saved-filter-views-v1',JSON.stringify(views))", stale_view)
            await page.reload(wait_until="networkidle")
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator("#saved-filter-view").select_option(label="Удалённый тег")
            result["checks"]["removedTagRemainsVisibleInSavedView"] = await page.locator("#filter-tag").input_value() == "Тег, которого больше нет" and await page.locator("#filter-tag").evaluate("el=>el.selectedOptions[0].textContent") == "Тег, которого больше нет" and await page.locator(".project-card").count() == 0

            seed = [{"id": f"seed-{i}", "name": f"Набор {i}", "filters": {"query": f"query-{i}", "type": "Все типы", "status": "Все статусы", "tag": "Все теги", "sort": "featured", "featuredOnly": False}} for i in range(12)]
            await page.evaluate("views=>localStorage.setItem('folio-saved-filter-views-v1',JSON.stringify(views))", seed)
            await page.reload(wait_until="networkidle")
            await page.locator('nav [data-view="projects"]:visible').click()
            result["checks"]["limitIsTwelveAndEnforced"] = await page.locator(".saved-view-limit").inner_text() == "12/12" and await page.locator('[data-action="save-filter-view"]').is_disabled()
            await page.evaluate("localStorage.setItem('folio-saved-filter-views-v1','{broken')")
            await page.reload(wait_until="networkidle")
            await page.locator('nav [data-view="projects"]:visible').click()
            result["checks"]["malformedPreferenceFailsClosed"] = await page.locator("#saved-filter-view option").count() == 1 and await page.locator(".saved-view-limit").inner_text() == "0/12"
            assert all(result["checks"].values()), {**result, "toolbar": bounds}
            assert not result["errors"], result["errors"]
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (QA / "web-saved-filters-v53-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
