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

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"
WEB = ROOT / "web"
FIXTURE = PACKAGE / "04_QA_доказательства" / "fixtures" / "sw-upgrade-v57-v58" / "web-v57"
QA = PACKAGE / "04_QA_доказательства"
TEMP = Path(tempfile.mkdtemp(prefix="folio-sw-v57-v58-"))
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
    for filename in ("app.js", "styles.css", "sw.js"):
        shutil.copy2(FIXTURE / filename, SITE / filename)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result = {"from": "folio-shell-v57-sticky-dialog-heading", "to": "folio-shell-v58-illustrated-dashboard-hero", "checks": {}, "screens": [], "errors": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda message: result["errors"].append(message.text) if message.type == "error" else None)
            base = f"http://127.0.0.1:{server.server_port}/"
            await page.goto(base + "#dashboard", wait_until="networkidle", timeout=20000)
            await page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15000)
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v57-sticky-dialog-heading')", timeout=15000)
            await page.reload(wait_until="networkidle")
            project_ids_before = await page.evaluate("""async()=>new Promise((resolve,reject)=>{const request=indexedDB.open('folio-workspace',1);request.onsuccess=()=>{const get=request.result.transaction('records','readonly').objectStore('records').get('portfolio');get.onsuccess=()=>resolve((get.result?.value?.projects||[]).map(project=>project.id));get.onerror=()=>reject(get.error)};request.onerror=()=>reject(request.error)})""")
            assert len(project_ids_before) == 3, project_ids_before
            result["checks"]["v57ControlsOfflineShellAndThreePortfolioRecords"] = True
            for filename in ("app.js", "styles.css", "sw.js"):
                shutil.copy2(WEB / filename, SITE / filename)
            shutil.copy2(WEB / "assets" / "illustrations" / "folio-dashboard-hero-v1.webp", SITE / "assets" / "illustrations" / "folio-dashboard-hero-v1.webp")
            await page.evaluate("navigator.serviceWorker.ready.then(registration=>registration.update())")
            await page.wait_for_selector("#update-notice:not([hidden])", timeout=15000)
            result["checks"]["updateNoticeWaitsForUserConfirmation"] = await page.locator("#update-reload").inner_text() == "Перезапустить" and await page.locator("#update-notice").is_visible()
            await page.screenshot(path=str(QA / "web-update-v57-v58-hero-notice-1440x900.png"))
            result["screens"].append("web-update-v57-v58-hero-notice-1440x900.png")
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v58-illustrated-dashboard-hero')", timeout=10000)
            result["checks"]["newShellIsCachedBeforeReload"] = await page.evaluate("""async()=> (await caches.keys()).includes('folio-shell-v58-illustrated-dashboard-hero')""")
            await page.locator("#update-reload").click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector(".dashboard-hero-art")
            ids_after = await page.evaluate("""async()=>new Promise((resolve,reject)=>{const request=indexedDB.open('folio-workspace',1);request.onsuccess=()=>{const get=request.result.transaction('records','readonly').objectStore('records').get('portfolio');get.onsuccess=()=>resolve((get.result?.value?.projects||[]).map(project=>project.id));get.onerror=()=>reject(get.error)};request.onerror=()=>reject(request.error)})""")
            result["checks"]["portfolioRecordsSurviveConfirmedUpdate"] = ids_after == project_ids_before
            result["checks"]["newIllustrationLoadsAfterUpdate"] = await page.locator(".dashboard-hero-art").evaluate("img=>img.complete&&img.naturalWidth>0")
            result["checks"]["oldVersionCacheIsRemoved"] = await page.evaluate("async()=>{const keys=(await caches.keys()).filter(key=>key.startsWith('folio-shell-'));return keys.length===1&&keys[0]==='folio-shell-v58-illustrated-dashboard-hero'}")
            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_selector(".dashboard-hero-art")
            result["checks"]["updatedDashboardAndIllustrationLoadOffline"] = await page.locator(".dashboard-hero-art").evaluate("img=>img.complete&&img.naturalWidth>0")
            result["checks"]["portfolioRecordsSurviveOfflineReload"] = await page.evaluate("""async()=>new Promise((resolve,reject)=>{const request=indexedDB.open('folio-workspace',1);request.onsuccess=()=>{const get=request.result.transaction('records','readonly').objectStore('records').get('portfolio');get.onsuccess=()=>resolve((get.result?.value?.projects||[]).length===3);get.onerror=()=>reject(get.error)};request.onerror=()=>reject(request.error)})""")
            await page.screenshot(path=str(QA / "web-update-v58-offline-hero-1440x900.png"))
            result["screens"].append("web-update-v58-offline-hero-1440x900.png")
            result["checks"]["noApplicationErrors"] = not result["errors"]
            assert all(result["checks"].values()), result
            await context.set_offline(False)
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    (QA / "web-update-v57-v58-hero-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TEMP, ignore_errors=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


asyncio.run(main())
