from __future__ import annotations

import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
QA = Path(__file__).resolve().parent
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


async def portfolio_snapshot(page) -> str:
    return await page.evaluate("""async()=>{
      const request=indexedDB.open('folio-workspace',1);
      return await new Promise((resolve,reject)=>{
        request.onerror=()=>reject(request.error);
        request.onsuccess=()=>{
          const db=request.result,read=db.transaction('records','readonly').objectStore('records').get('portfolio');
          read.onerror=()=>reject(read.error);
          read.onsuccess=()=>resolve(JSON.stringify(read.result?.value??null));
        };
      });
    }""")


async def main() -> None:
    if not CHROME.exists():
        raise RuntimeError(f"Chrome executable not found: {CHROME}")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(WEB)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    result = {"date": "2026-10-30", "purpose": "preview-first static showcase download, focus return and no data mutation",
              "viewports": {}, "confirmed": False}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME),
                args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle", timeout=20000)
            navigation = []
            for route in ("dashboard", "projects", "showcase", "settings"):
                await page.locator(f'.nav-item[data-view="{route}"]').click()
                heading = page.locator('#main-content h1')
                await heading.wait_for(state="visible")
                navigation.append({"route": route, "heading": await heading.inner_text()})
            result["navigation"] = navigation
            await page.locator('.nav-item[data-view="showcase"]').click()
            await page.locator('#showcase-theme').select_option('night')
            button = page.locator('[data-action="preview-static"]')
            await button.wait_for(state="visible")
            before = await portfolio_snapshot(page)
            await button.click()
            dialog = page.locator('#showcase-preview-dialog')
            await dialog.wait_for(state="visible")
            frame = page.frame_locator('#showcase-preview-frame')
            await frame.locator('h1').wait_for(state="visible")
            desktop = await frame.locator('body').evaluate("el=>({title:el.ownerDocument.title,projects:el.querySelectorAll('.project').length,scriptCount:el.querySelectorAll('script').length,imageCount:el.querySelectorAll('img').length,imagesLoaded:[...el.querySelectorAll('img')].every(img=>img.complete&&img.naturalWidth>0),theme:el.ownerDocument.body.className,width:el.ownerDocument.documentElement.scrollWidth})")
            await frame.locator('.project').evaluate("el=>el.getAnimations().forEach(animation=>animation.finish())")
            desktop["dialogVisible"] = await dialog.is_visible()
            desktop["iframeTitle"] = await page.locator('#showcase-preview-frame').get_attribute('title')
            desktop["sandbox"] = await page.locator('#showcase-preview-frame').get_attribute('sandbox')
            desktop["documentWidth"] = await page.evaluate('document.documentElement.scrollWidth')
            desktop["viewportWidth"] = 1440
            await page.screenshot(path=str(QA / "showcase-export-preview-desktop-1440x900.png"), full_page=False)
            result["viewports"]["desktop_1440x900"] = desktop
            await page.keyboard.press("Escape")
            result["escapeClosedDesktop"] = not await dialog.is_visible()
            result["focusReturnedDesktop"] = await button.evaluate("el=>document.activeElement===el")
            async with page.expect_download() as download_info:
                await page.locator('[data-action="export-static"]').click()
                export_dialog = page.locator('#showcase-preview-dialog')
                await export_dialog.wait_for(state="visible")
                export_frame = page.frame_locator('#showcase-preview-frame')
                await export_frame.locator('h1').wait_for(state="visible")
                await page.locator('#showcase-export-download').click()
            download = await download_info.value
            exported_html = Path(await download.path()).read_text(encoding="utf-8")
            result["download"] = {"filename": download.suggested_filename,
                "selfContainedImage": "data:image/" in exported_html,
                "containsFeaturedCase": "Портфолио веб-разработчика" in exported_html,
                "containsNoScript": "<script" not in exported_html.lower(),
                "selectedTheme": 'class="theme-night"' in exported_html}

            mobile_page = await context.new_page()
            mobile_page.on("pageerror", lambda error: errors.append(str(error)))
            await mobile_page.set_viewport_size({"width": 390, "height": 844})
            await mobile_page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle", timeout=20000)
            await mobile_page.locator('.mobile-nav-item[data-view="showcase"]').click()
            await mobile_page.locator('#showcase-theme').select_option('gallery')
            mobile_button = mobile_page.locator('[data-action="preview-static"]')
            await mobile_button.wait_for(state="visible")
            await mobile_button.click()
            mobile_dialog = mobile_page.locator('#showcase-preview-dialog')
            await mobile_dialog.wait_for(state="visible")
            mobile_frame = mobile_page.frame_locator('#showcase-preview-frame')
            await mobile_frame.locator('h1').wait_for(state="visible")
            mobile = await mobile_frame.locator('body').evaluate("el=>({projects:el.querySelectorAll('.project').length,scriptCount:el.querySelectorAll('script').length,theme:el.ownerDocument.body.className,width:el.ownerDocument.documentElement.scrollWidth})")
            await mobile_frame.locator('.project').evaluate("el=>el.getAnimations().forEach(animation=>animation.finish())")
            mobile["dialogVisible"] = await mobile_dialog.is_visible()
            mobile["outerWidth"] = await mobile_page.evaluate('document.documentElement.scrollWidth')
            mobile["viewportWidth"] = 390
            mobile["dialogBounds"] = await mobile_dialog.evaluate("el=>{const r=el.getBoundingClientRect();return {width:Math.round(r.width),height:Math.round(r.height),left:Math.round(r.left),top:Math.round(r.top)}}")
            await mobile_page.screenshot(path=str(QA / "showcase-export-preview-mobile-390x844.png"), full_page=False)
            result["viewports"]["mobile_390x844"] = mobile
            await mobile_page.keyboard.press("Escape")
            result["escapeClosedMobile"] = not await mobile_dialog.is_visible()
            result["focusReturnedMobile"] = await mobile_button.evaluate("el=>document.activeElement===el")
            after = await portfolio_snapshot(mobile_page)
            result["portfolioUnchanged"] = before == after
            result["browserErrors"] = errors
            result["confirmed"] = bool(
                desktop["dialogVisible"] and desktop["projects"] == 1 and desktop["scriptCount"] == 0
                and desktop["imagesLoaded"] and desktop["theme"] == "theme-night" and desktop["iframeTitle"] and "allow-same-origin" in desktop["sandbox"]
                and desktop["documentWidth"] == desktop["viewportWidth"]
                and mobile["dialogVisible"] and mobile["projects"] == 1 and mobile["scriptCount"] == 0
                and mobile["outerWidth"] == 390 and mobile["dialogBounds"]["left"] == 0
                and [item["route"] for item in navigation] == ["dashboard", "projects", "showcase", "settings"]
                and result["escapeClosedDesktop"] and result["focusReturnedDesktop"]
                and result["download"]["filename"] == "folio-showcase.html"
                and result["download"]["selfContainedImage"] and result["download"]["containsFeaturedCase"]
                and result["download"]["containsNoScript"] and result["download"]["selectedTheme"]
                and mobile["theme"] == "theme-gallery"
                and result["escapeClosedMobile"] and result["focusReturnedMobile"] and result["portfolioUnchanged"]
                and not errors
            )
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (QA / "showcase-export-preview-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["confirmed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
