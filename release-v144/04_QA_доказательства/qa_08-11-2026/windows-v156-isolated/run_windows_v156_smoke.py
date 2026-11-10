from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright


OUT = Path(__file__).resolve().parent
URL = os.environ.get("FOLIO_V156_AUDIT_URL", "http://127.0.0.1:41766/")
CHROME = Path(os.environ.get("FOLIO_CHROME_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))


async def route_snapshot(page, route: str) -> dict:
    if route != "dashboard":
        await page.locator(f'[data-view="{route}"]:visible').first.click()
    await page.locator("#main-content h1").first.wait_for(state="visible")
    await page.wait_for_timeout(120)
    record = await page.evaluate(
        """() => ({
          route: location.hash.slice(1) || 'dashboard',
          title: document.querySelector('#main-content h1')?.innerText.trim() || '',
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          projectCards: document.querySelectorAll('.project-card').length,
          brokenImages: [...document.querySelectorAll('.project-card img')].filter(image => image.complete && image.naturalWidth === 0).length,
          serviceWorkerControlled: Boolean(navigator.serviceWorker?.controller),
        })"""
    )
    record["viewport"] = [await page.evaluate("innerWidth"), await page.evaluate("innerHeight")]
    record["noHorizontalOverflow"] = record["documentWidth"] <= record["viewport"][0] and record["bodyWidth"] <= record["viewport"][0]
    return record


async def main() -> None:
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    records: list[dict] = []
    screenshots: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'", timeout=20000)
        await page.wait_for_function("document.querySelectorAll('.project-card').length === 3", timeout=15000)

        desktop = await route_snapshot(page, "dashboard")
        desktop_shot = OUT / "v156-desktop-dashboard.png"
        await page.screenshot(path=str(desktop_shot), full_page=False)
        screenshots.append({"file": desktop_shot.name, "viewport": desktop["viewport"], "sha256": hashlib.sha256(desktop_shot.read_bytes()).hexdigest()})

        for route in ("projects", "showcase", "settings", "dashboard"):
            records.append(await route_snapshot(page, route))

        await page.set_viewport_size({"width": 390, "height": 844})
        for route in ("dashboard", "projects", "showcase", "settings"):
            if route == "dashboard":
                await page.locator('[data-view="dashboard"]:visible').first.click()
            records.append(await route_snapshot(page, route))
            if route in ("dashboard", "projects"):
                shot = OUT / f"v156-mobile-{route}.png"
                await page.screenshot(path=str(shot), full_page=False)
                screenshots.append({"file": shot.name, "viewport": [390, 844], "sha256": hashlib.sha256(shot.read_bytes()).hexdigest()})

        await page.set_viewport_size({"width": 320, "height": 568})
        for route in ("dashboard", "projects", "showcase", "settings"):
            await page.locator(f'[data-view="{route}"]:visible').first.click()
            records.append(await route_snapshot(page, route))

        await page.set_viewport_size({"width": 390, "height": 844})
        await page.locator('[data-view="dashboard"]:visible').first.click()
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("Boolean(navigator.serviceWorker?.controller)", timeout=15000)
        await context.set_offline(True)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'", timeout=15000)
        await page.wait_for_function("document.querySelectorAll('.project-card').length === 3", timeout=15000)
        offline = await route_snapshot(page, "dashboard")
        offline["online"] = await page.evaluate("navigator.onLine")
        shot = OUT / "v156-mobile-offline-dashboard.png"
        await page.screenshot(path=str(shot), full_page=False)
        screenshots.append({"file": shot.name, "viewport": [390, 844], "sha256": hashlib.sha256(shot.read_bytes()).hexdigest()})
        await context.set_offline(False)
        await browser.close()

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "webview2_build": "v156",
        "shared_web_assets": "v153",
        "url": URL,
        "http_status": response.status if response else None,
        "browser": "Installed Chrome, isolated Playwright context against the exact v156 local host",
        "initial_dashboard": desktop,
        "route_matrix": records,
        "offline_cold_reload": offline,
        "browser_errors": errors,
        "screenshots": screenshots,
        "data_scope": "fresh Playwright browser context and dedicated v156 host profile; no user browser profile or portfolio database used",
        "limits": ["The host is the exact v156 executable; page rendering was cross-checked in Chromium, while the native WebView2 window was separately opened and visually inspected."],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"http_status": result["http_status"], "initial_dashboard": desktop, "route_count": len(records), "offline": offline, "errors": errors, "screenshots": screenshots}, ensure_ascii=False, indent=2))
    failures = [row for row in [desktop, *records, offline] if not row["noHorizontalOverflow"] or row["brokenImages"]]
    if response is None or response.status != 200 or errors or failures or offline["online"] or not offline["serviceWorkerControlled"]:
        raise SystemExit("Windows v156 isolated browser smoke failed")


if __name__ == "__main__":
    asyncio.run(main())
