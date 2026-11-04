from __future__ import annotations

import asyncio
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"
OUT = Path(__file__).resolve().parent
PORT = 8772


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


async def main():
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(WEB), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            )
            context = await browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=1,
                is_mobile=True,
                has_touch=True,
                service_workers="block",
            )
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = await page.goto(f"http://127.0.0.1:{PORT}/#dashboard", wait_until="networkidle")
            await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') !== 'true'")
            mobile_projects = page.locator('.mobile-nav-item[data-view="projects"]')
            if await mobile_projects.count() != 1:
                nav_debug = await page.locator("body").inner_text()
                raise AssertionError(f"Expected one mobile projects control; url={page.url}, body={nav_debug[:300]!r}")
            await mobile_projects.dispatch_event("click")
            await page.wait_for_timeout(200)
            measurements = await page.locator(".filter-panel select").evaluate_all(
                "items => items.map(item => ({label: item.labels?.[0]?.innerText || item.getAttribute('aria-label') || item.name, "
                "height: Math.round(item.getBoundingClientRect().height), minHeight: getComputedStyle(item).minHeight}))"
            )
            layout = await page.evaluate("({viewport: innerWidth, document: document.documentElement.scrollWidth, "
                                         "cards: document.querySelectorAll('.project-card').length})")
            screenshot = OUT / "mobile-filter-target-390x844.png"
            await page.screenshot(path=str(screenshot), animations="disabled")
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    result = {
        "build": "v101-mobile-filter-target",
        "viewport": "390x844",
        "status": "PASS",
        "http_status": response.status if response else None,
        "filters": measurements,
        "layout": layout,
        "page_errors": errors,
        "screenshot": screenshot.name,
    }
    if not response or response.status != 200 or not measurements or any(item["height"] < 44 for item in measurements):
        result["status"] = "FAIL"
    if layout["viewport"] != layout["document"] or not layout["cards"] or errors:
        result["status"] = "FAIL"
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
