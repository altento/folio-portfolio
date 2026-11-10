from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent / "effective-zoom-proxy-720x450"
URL = "http://127.0.0.1:8766/"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
VIEWPORT = {"width": 720, "height": 450}
ROUTES = ("dashboard", "projects", "showcase", "settings")


async def navigate(page, route: str) -> None:
    current = await page.evaluate("""() => {
      const active = [...document.querySelectorAll('[data-view][aria-current="page"]')]
        .find(element => element.getClientRects().length > 0);
      return active?.dataset.view || null;
    }""")
    if current != route:
        await page.locator(f'[data-view="{route}"]:visible').first.click()
    await page.wait_for_function("route => [...document.querySelectorAll('[data-view][aria-current=\"page\"]')].some(element => element.dataset.view === route && element.getClientRects().length > 0)", arg=route)
    await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'")
    await page.wait_for_timeout(80)


async def inspect(page, route: str, theme: str, results: list[dict]) -> None:
    await page.evaluate("window.scrollTo(0, 0)")
    state = await page.evaluate("""() => {
      const width = window.innerWidth;
      const visible = element => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' &&
          Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
      };
      const controls = [...document.querySelectorAll('button,a,input,select,textarea,summary,[tabindex]')]
        .filter(visible).map(element => {
          const rect = element.getBoundingClientRect();
          return {
            tag: element.tagName.toLowerCase(),
            id: element.id || null,
            label: (element.getAttribute('aria-label') || element.innerText || element.value || '').trim().slice(0, 70),
            left: Math.round(rect.left * 10) / 10,
            right: Math.round(rect.right * 10) / 10,
            top: Math.round(rect.top * 10) / 10,
            bottom: Math.round(rect.bottom * 10) / 10,
            width: Math.round(rect.width * 10) / 10,
            height: Math.round(rect.height * 10) / 10,
            fixed: getComputedStyle(element).position === 'fixed'
          };
        });
      const outOfHorizontalBounds = controls.filter(control => control.left < -1 || control.right > width + 1);
      const main = document.querySelector('#main-content');
      const active = [...document.querySelectorAll('[data-view][aria-current="page"]')]
        .find(element => element.getClientRects().length > 0);
      return {
        title: document.title,
        theme: document.documentElement.dataset.theme || 'light',
        viewport: [width, window.innerHeight],
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
        mainWidth: main?.clientWidth ?? null,
        mainScrollWidth: main?.scrollWidth ?? null,
        horizontalOverflow: document.documentElement.scrollWidth > width || document.body.scrollWidth > width,
        visibleControls: controls.length,
        controlsOutOfHorizontalBounds: outOfHorizontalBounds,
        navVisible: !!document.querySelector('.mobile-nav') && visible(document.querySelector('.mobile-nav')),
        activeRoute: active?.dataset.view || null,
        activeHeading: main?.querySelector('h1,h2')?.innerText?.trim() || null
      };
    }""")
    state["route"] = route
    state["themeExpected"] = theme
    screenshot = f"{route}-{theme}-720x450.png"
    await page.screenshot(path=str(OUTPUT / screenshot), full_page=False)
    state["screenshot"] = screenshot
    state["passed"] = (
        state["theme"] == theme
        and state["activeRoute"] == route
        and not state["horizontalOverflow"]
        and not state["controlsOutOfHorizontalBounds"]
        and state["visibleControls"] > 0
    )
    results.append(state)


async def main() -> None:
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result: dict = {"date": "2026-11-10", "url": URL, "viewport": [720, 450],
                    "interpretation": "Viewport proxy for a 1440x900 CSS workspace at nominal 200% scale; not a system magnifier test.",
                    "states": [], "browserErrors": []}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        context = await browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = await context.new_page()
        page.on("pageerror", lambda error: result["browserErrors"].append(str(error)))
        page.on("console", lambda message: result["browserErrors"].append(message.text)
                if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle", timeout=20000)
        result["httpStatus"] = response.status if response else None
        await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'")

        for route in ROUTES:
            await navigate(page, route)
            await inspect(page, route, "light", result["states"])

        await page.locator("#theme-toggle").click()
        result["darkThemeActivated"] = await page.evaluate("document.documentElement.dataset.theme === 'dark'")
        for route in ROUTES:
            await navigate(page, route)
            await inspect(page, route, "dark", result["states"])

        await browser.close()

    result["passCount"] = sum(bool(state["passed"]) for state in result["states"])
    result["allStatesPassed"] = result["passCount"] == len(result["states"]) and not result["browserErrors"]
    (OUTPUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result["allStatesPassed"]:
        raise SystemExit(1)


asyncio.run(main())
