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
NEW_WEB = QA.parent / "02_Приложение" / "web"
OLD_WEB = QA / "fixtures" / "sw-upgrade-v49-v50" / "v49-overlay"
TEMP = Path(tempfile.mkdtemp(prefix="folio-v49-v53-update-"))
SITE = TEMP / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *_args):
        pass


async def main():
    shutil.copytree(NEW_WEB, SITE)
    for source in OLD_WEB.rglob("*"):
        if source.is_file():
            target = SITE / source.relative_to(OLD_WEB)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    result = {"migration": {}, "record": {}, "errors": []}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v49-manual-update-notice')", timeout=15000)
            await page.wait_for_function("navigator.serviceWorker.controller!==null", timeout=15000)
            await page.reload(wait_until="networkidle", timeout=20000)

            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            form = page.locator("#project-form")
            await form.locator('[name="title"]').fill("Переход v49 → v53")
            await form.locator('[name="description"]').fill("Запись должна пережить замену service worker и офлайн-перезапуск.")
            await form.locator('[name="created_at"]').fill("2026-10-30")
            if await form.locator('[name="tags"]').count():
                await form.locator('[name="tags"]').fill("обновление, local-first")
            await form.locator('[type="submit"]').click()
            await page.get_by_text("Переход v49 → v53", exact=True).first.wait_for(timeout=10000)
            result["record"]["createdInOldVersion"] = True

            for source in NEW_WEB.rglob("*"):
                if source.is_file():
                    target = SITE / source.relative_to(NEW_WEB)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            (SITE / "sw.js").touch()
            changed = await page.evaluate("""async()=>{const registration=await navigator.serviceWorker.getRegistration();const change=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));await registration.update();return Promise.race([change,new Promise(resolve=>setTimeout(()=>resolve(false),15000))])}""")
            await page.locator("#update-notice").wait_for(state="visible", timeout=10000)
            result["migration"].update({"controllerChanged": changed, "noticeVisible": await page.locator("#update-notice").is_visible()})
            await page.screenshot(path=str(QA / "web-update-v49-v53-notice-1440x900.png"))
            assert result["migration"]["controllerChanged"] and result["migration"]["noticeVisible"]
            await page.locator("#update-reload").click()
            await page.wait_for_load_state("domcontentloaded", timeout=12000)
            await page.locator("#update-notice").wait_for(state="hidden", timeout=10000)
            await page.wait_for_function("async()=>{const keys=await caches.keys();return keys.length===1&&keys[0]==='folio-shell-v53-saved-filter-views'}", timeout=15000)
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.get_by_text("Переход v49 → v53", exact=True).first.wait_for(timeout=10000)
            result["record"]["retainedAfterUpgrade"] = True
            result["migration"]["savedViewsAvailable"] = await page.locator("#saved-filter-view").count() == 1
            await page.locator("#search-input").fill("Переход v49")
            await page.locator('[data-action="save-filter-view"]').click()
            await page.locator("#saved-filter-name").fill("После обновления")
            await page.locator('#saved-filter-form button[type="submit"]').click()
            result["record"]["savedViewAfterUpgrade"] = await page.locator("#saved-filter-view").input_value() != ""
            await page.screenshot(path=str(QA / "web-update-v53-saved-views-1440x900.png"))
            assert result["migration"]["savedViewsAvailable"] and result["record"]["savedViewAfterUpgrade"]
            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded", timeout=12000)
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator("#saved-filter-view").select_option(label="После обновления")
            await page.get_by_text("Переход v49 → v53", exact=True).first.wait_for(timeout=10000)
            result["record"]["retainedOffline"] = True
            result["record"]["savedViewRetainedOffline"] = await page.locator("#search-input").input_value() == "Переход v49"
            result["migration"]["cacheKeys"] = await page.evaluate("caches.keys()")
            assert result["migration"]["cacheKeys"] == ["folio-shell-v53-saved-filter-views"]
            assert result["record"]["savedViewRetainedOffline"]
            assert not result["errors"], result["errors"]
            await context.set_offline(False)
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()

    (QA / "web-update-v49-v53-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
