from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright


OUTPUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:41823/"


async def main() -> None:
    errors: list[str] = []
    checks: list[dict] = []
    chrome = Path(os.environ.get("FOLIO_CHROME_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    if not chrome.is_file():
        raise FileNotFoundError(f"Chrome executable not found: {chrome}")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=str(chrome))
        context = await browser.new_context(
            viewport={"width": 390, "height": 568},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
        )
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle")
        await page.locator('button[data-view="projects"]:visible').first.click()
        await page.locator("#search-input").wait_for(state="visible")
        await page.locator("#search-input").fill("CRM")
        await page.locator("#reset-filters:not([hidden])").wait_for(state="visible")
        await page.wait_for_timeout(150)

        for width, height in ((390, 568), (390, 844), (320, 568), (1440, 900)):
            await page.set_viewport_size({"width": width, "height": height})
            await page.wait_for_timeout(100)
            state = await page.evaluate("""() => {
              const visible = element => !!element && element.getClientRects().length > 0;
              const styles = selector => [...document.querySelectorAll(selector)].filter(visible).map(element => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return {label: element.innerText.trim(), fontSize: parseFloat(style.fontSize), height: Math.round(rect.height), width: Math.round(rect.width)};
              });
              return {
                viewport: [innerWidth, innerHeight],
                documentWidth: document.documentElement.scrollWidth,
                bodyWidth: document.body.scrollWidth,
                visibleProjects: document.querySelectorAll('.project-card').length,
                resetVisible: visible(document.querySelector('#reset-filters')),
                selectLabel: styles('.results-actions .select-visible-control span'),
                viewButtons: styles('.results-actions .view-toggle button'),
                resetButton: styles('.results-actions #reset-filters'),
                touchTargets: styles('.results-actions .select-visible-control, .results-actions .view-toggle button, .results-actions #reset-filters'),
              };
            }""")
            state["noHorizontalOverflow"] = state["documentWidth"] <= width and state["bodyWidth"] <= width
            min_font_size = 10 if width <= 400 else 9
            state["toolbarTextReadable"] = all(
                item["fontSize"] >= min_font_size
                for key in ("selectLabel", "viewButtons", "resetButton")
                for item in state[key]
            )
            state["touchTargetsAtLeast44px"] = all(item["height"] >= 44 for item in state["touchTargets"])
            checks.append(state)
            if width == 390 and height == 568:
                screenshot = OUTPUT / "mobile-toolbar-390x568.png"
                await page.screenshot(path=str(screenshot), full_page=False)

        await page.locator("#reset-filters:not([hidden])").click()
        await page.wait_for_timeout(100)
        reset_state = await page.evaluate("""() => ({
          query: document.querySelector('#search-input')?.value,
          projectCount: document.querySelectorAll('.project-card').length,
          resetHidden: document.querySelector('#reset-filters')?.hidden,
        })""")
        await browser.close()

    screenshot_path = OUTPUT / "mobile-toolbar-390x568.png"
    result = {
        "date": "2026-11-07",
        "build": "Web/PWA v152 readability fix",
        "profile": "new isolated Playwright context",
        "url": URL,
        "http_status": response.status if response else None,
        "viewport_checks": checks,
        "reset_flow": reset_state,
        "page_or_console_errors": errors,
        "screenshot": {
            "file": screenshot_path.name,
            "sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
        },
    }
    (OUTPUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if response is None or response.status != 200 or errors or not reset_state["resetHidden"]:
        raise SystemExit("Mobile toolbar smoke failed")
    if reset_state["query"] or reset_state["projectCount"] != 3:
        raise SystemExit("Reset filter did not restore the complete demo list")
    if not all(item["noHorizontalOverflow"] and item["toolbarTextReadable"] and item["touchTargetsAtLeast44px"] for item in checks):
        raise SystemExit("Toolbar readability or horizontal overflow regression")


if __name__ == "__main__":
    asyncio.run(main())
