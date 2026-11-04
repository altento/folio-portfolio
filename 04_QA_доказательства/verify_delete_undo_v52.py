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
TEMP = Path(tempfile.mkdtemp(prefix="folio-v52-undo-"))
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
    result = {"version": "v52-delete-undo", "checks": {}, "errors": []}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            assert response and response.status == 200
            await page.locator('.sidebar [data-view="projects"]').click()
            card = page.locator(".project-card").first
            title = await card.locator(".card-title").inner_text()
            await card.locator("[data-detail]").click()
            await page.locator("#detail-dialog [data-delete]").click()
            await page.locator("#detail-dialog").wait_for(state="hidden")
            toast = page.locator("#toast-region .toast")
            await toast.wait_for(state="visible")
            result["checks"]["deleteClosesDetailsAndShowsUndo"] = "Отменить" in await toast.inner_text()
            case_title = page.locator(".project-card .card-title").filter(has_text=title)
            result["checks"]["deletedCardDisappears"] = await case_title.count() == 0
            await page.screenshot(path=str(QA / "web-delete-undo-v52-desktop.png"), full_page=True)
            assert result["checks"]["deleteClosesDetailsAndShowsUndo"] and result["checks"]["deletedCardDisappears"], result
            await toast.locator(".toast-action").click()
            await page.locator('.sidebar [data-view="projects"]').click()
            result["checks"]["undoRestoresOriginalCase"] = await page.locator(".project-card .card-title").filter(has_text=title).count() == 1
            await page.locator("#toast-region .toast").wait_for(state="visible")
            result["checks"]["undoAnnounced"] = "восстановлен" in (await page.locator("#toast-region").inner_text()).lower()
            await page.set_viewport_size({"width": 390, "height": 844})
            result["checks"]["mobileHasNoHorizontalOverflow"] = await page.evaluate("document.documentElement.scrollWidth===innerWidth")
            await page.locator("#toast-region .toast").wait_for(state="hidden", timeout=5000)
            await page.screenshot(path=str(QA / "web-delete-undo-v52-mobile-390x844.png"))
            await page.locator(".project-card [data-detail]").first.click()
            await page.locator("#detail-dialog [data-delete]").click()
            await page.locator("#toast-region .toast").wait_for(state="visible", timeout=5000)
            await page.locator("#toast-region .toast").wait_for(state="hidden", timeout=9000)
            await page.wait_for_timeout(150)
            result["checks"]["focusReturnsAfterUndoExpires"] = await page.evaluate("document.activeElement.matches('#main-content h1')")
            assert all(result["checks"].values()), result
            assert not result["errors"], result["errors"]
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (QA / "web-delete-undo-v52-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
