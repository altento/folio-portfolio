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
WEB = ROOT / "web"
QA = Path(__file__).resolve().parent
TEMP = Path(tempfile.mkdtemp(prefix="folio-dashboard-hero-v58-"))
SITE = TEMP / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
IMAGE = "./assets/illustrations/folio-dashboard-hero-v1.webp"


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *_args):
        pass


async def main():
    shutil.copytree(WEB, SITE)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result = {"version": "folio-shell-v58-illustrated-dashboard-hero", "checks": {}, "screens": [], "errors": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME), args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda message: result["errors"].append(message.text) if message.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            assert response and response.status == 200
            hero = page.locator(".dashboard-hero")
            art = page.locator(".dashboard-hero-art")
            await hero.wait_for(state="visible")
            await page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=await art.element_handle(), timeout=10000)
            result["checks"]["heroContainsLocalGeneratedArtwork"] = await art.get_attribute("src") == IMAGE and await art.get_attribute("alt") == "" and await art.get_attribute("aria-hidden") == "true"
            result["checks"]["heroHasHeadingAndPrimaryAction"] = await hero.locator("h1").count() == 1 and await hero.locator('[data-action="new-project"]').is_visible()
            for width, height, label in [(1440, 900, "desktop-1440x900"), (390, 844, "mobile-390x844"), (320, 568, "mobile-320x568")]:
                await page.set_viewport_size({"width": width, "height": height})
                metrics = await hero.evaluate("""el => {const h=el.getBoundingClientRect(),i=el.querySelector('img').getBoundingClientRect(),a=el.querySelector('[data-action="new-project"]').getBoundingClientRect();return {viewport:innerWidth,document:document.documentElement.scrollWidth,hero:{x:Math.round(h.x),y:Math.round(h.y),width:Math.round(h.width),height:Math.round(h.height)},image:{x:Math.round(i.x),y:Math.round(i.y),width:Math.round(i.width),height:Math.round(i.height)},actionVisible:a.width>0&&a.height>0&&a.left>=0&&a.right<=innerWidth}}""")
                assert metrics["document"] == width and metrics["image"]["width"] > 0 and metrics["image"]["height"] > 0 and metrics["actionVisible"], metrics
                result["checks"][label] = metrics
                screenshot = f"web-dashboard-hero-v58-{label}.png"
                await page.screenshot(path=str(QA / screenshot), full_page=False)
                result["screens"].append(screenshot)
            await page.locator("#theme-toggle").click()
            result["checks"]["darkThemeHeadingReadable"] = await page.locator(".dashboard-hero h1").evaluate("el => getComputedStyle(el).color") == "rgb(32, 33, 38)"
            await page.locator("#theme-toggle").click()
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v58-illustrated-dashboard-hero')", timeout=15000)
            result["checks"]["serviceWorkerCachesHeroAsset"] = await page.evaluate("""async path => {const cache=await caches.open('folio-shell-v58-illustrated-dashboard-hero');return !!await cache.match(path)}""", IMAGE)
            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_selector(".dashboard-hero-art")
            result["checks"]["dashboardLoadsAfterOfflineReload"] = await page.locator(".dashboard-hero-art").evaluate("img => img.complete && img.naturalWidth > 0")
            await context.set_offline(False)
            result["checks"]["noApplicationErrors"] = not result["errors"]
            assert all(result["checks"].values()), result
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    (QA / "web-dashboard-hero-v58-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TEMP, ignore_errors=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


asyncio.run(main())
