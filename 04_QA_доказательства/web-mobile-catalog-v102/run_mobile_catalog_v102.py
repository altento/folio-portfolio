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
PORT = 8773


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


async def main():
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(WEB), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    results = {"build": "v102-mobile-catalog-disclosure", "status": "PASS", "sizes": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            )
            context = await browser.new_context(viewport={"width": 390, "height": 844},
                                                device_scale_factor=1, is_mobile=True, has_touch=True,
                                                service_workers="block")
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{PORT}/#dashboard", wait_until="networkidle")
            await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') !== 'true'")
            await page.locator('.mobile-nav-item[data-view="projects"]').dispatch_event("click")
            await page.wait_for_selector(".project-card")

            await page.locator("#page-title").evaluate("element => element.blur()")
            for width, height in ((320, 568), (390, 844)):
                await page.set_viewport_size({"width": width, "height": height})
                await page.wait_for_timeout(100)
                measure = await page.evaluate("""() => {
                  const card=document.querySelector('.project-card'),dock=document.querySelector('.mobile-nav');
                  const rect=el=>{const r=el.getBoundingClientRect();return {top:Math.round(r.top),bottom:Math.round(r.bottom),height:Math.round(r.height)}};
                  return {viewportWidth:innerWidth,documentWidth:document.documentElement.scrollWidth,
                    card:card?rect(card):null,dock:dock?rect(dock):null,
                    cardVisibleAboveDock:!!card&&card.getBoundingClientRect().top<dock.getBoundingClientRect().top,
                    filterOpen:document.querySelector('#project-filter-disclosure')?.open,
                    savedViewsOpen:document.querySelector('#saved-views-disclosure')?.open,
                    filterControlsPresent:document.querySelectorAll('#project-filter-disclosure select').length,
                    selectionTargetHeight:Math.round(document.querySelector('.select-visible-control').getBoundingClientRect().height),
                    layoutButtonHeights:[...document.querySelectorAll('.view-toggle button')].map(item=>Math.round(item.getBoundingClientRect().height)),
                    selectionLabelSize:parseFloat(getComputedStyle(document.querySelector('.select-visible-control span')).fontSize)};
                }""")
                results["sizes"].append({"width": width, "height": height, **measure})
                await page.screenshot(path=str(OUT / f"catalog-collapsed-{width}x{height}.png"), animations="disabled")

            await page.locator('#project-filter-disclosure > summary').focus()
            await page.keyboard.press("Enter")
            if not await page.locator("#project-filter-disclosure").evaluate("element => element.open"):
                raise AssertionError("Filter disclosure did not open from the keyboard")
            await page.locator("#filter-type").select_option(label="Веб-приложение")
            preserved = await page.evaluate("""() => ({open:document.querySelector('#project-filter-disclosure').open,
              focusedId:document.activeElement?.id,selectedType:document.querySelector('#filter-type')?.value,
              activeBadge:document.querySelector('#project-filter-disclosure summary small')?.textContent.trim(),
              resultCount:document.querySelector('.result-summary b')?.textContent.trim()})""")
            if not preserved["open"] or preserved["focusedId"] != "filter-type" or preserved["selectedType"] != "Веб-приложение":
                raise AssertionError(f"Disclosure state or filter focus was lost on rerender: {preserved}")
            results["filter_interaction"] = preserved
            await page.screenshot(path=str(OUT / "filters-expanded-390x844.png"), animations="disabled")

            await page.locator('#saved-views-disclosure > summary').focus()
            await page.keyboard.press("Enter")
            controls_visible = await page.locator('[data-action="save-filter-view"]').is_visible()
            if not controls_visible:
                raise AssertionError("Saved view controls did not appear when disclosure opened")
            await page.locator('[data-action="save-filter-view"]').click()
            await page.wait_for_selector('#saved-filter-dialog[open]')
            await page.locator('#saved-filter-name').fill('QA каталог v102')
            await page.locator('#saved-filter-form button[type="submit"]').click()
            await page.locator('#saved-filter-dialog').wait_for(state='hidden')
            saved_view_id = await page.locator('#saved-filter-view').input_value()
            saved_label = await page.locator('#saved-views-disclosure > summary small').inner_text()
            await page.locator('#filter-type').select_option(label='Все типы')
            await page.locator('#saved-filter-view').select_option(saved_view_id)
            applied_view = await page.evaluate("""() => ({type:document.querySelector('#filter-type').value,
              savedDisclosureOpen:document.querySelector('#saved-views-disclosure').open,
              savedSummary:document.querySelector('#saved-views-disclosure summary small').textContent.trim()})""")
            if not saved_view_id or saved_label != 'Выбрана: QA каталог v102' or applied_view['type'] != 'Веб-приложение':
                raise AssertionError(f"Saved view did not round trip: {saved_label!r} {applied_view}")
            results['saved_view_round_trip'] = applied_view
            await page.locator('.mobile-nav-item[data-view="projects"]').evaluate("element => element.click()")
            await page.wait_for_timeout(100)
            await page.set_viewport_size({"width": 1440, "height": 900})
            await page.wait_for_timeout(100)
            desktop_open = await page.evaluate("""() => ({filters:document.querySelector('#project-filter-disclosure').open,
              savedViews:document.querySelector('#saved-views-disclosure').open,
              summaries:[...document.querySelectorAll('.project-filter-disclosure > summary,.saved-views-disclosure > summary')]
                .map(element=>getComputedStyle(element).display)})""")
            if not desktop_open["filters"] or not desktop_open["savedViews"]:
                raise AssertionError(f"Desktop controls should be expanded: {desktop_open}")
            results["desktop_resize"] = desktop_open
            results["page_errors"] = errors
            results["http_status"] = response.status if response else None
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()

    if not response or response.status != 200 or errors:
        results["status"] = "FAIL"
    if any(item["documentWidth"] != item["viewportWidth"] or not item["cardVisibleAboveDock"]
           or item["filterOpen"] or item["savedViewsOpen"] or item["selectionTargetHeight"] < 44
           or min(item["layoutButtonHeights"]) < 44 or item["selectionLabelSize"] < 11 for item in results["sizes"]):
        results["status"] = "FAIL"
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if results["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())


