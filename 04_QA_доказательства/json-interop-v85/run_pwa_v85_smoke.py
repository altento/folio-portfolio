from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8766/"
OUT = Path(__file__).resolve().parent


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="allow")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        response = page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise AssertionError(f"Application response was {response.status if response else 'missing'}")
        page.wait_for_timeout(1800)
        update_button = page.locator("#update-reload")
        if update_button.is_visible():
            update_button.click()
            page.wait_for_load_state("networkidle", timeout=15_000)
            page.wait_for_timeout(900)
        page.wait_for_function(
            "navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL.includes('sw.js')",
            timeout=15_000,
        )
        sw_version = page.evaluate("navigator.serviceWorker.controller?.scriptURL")
        cache_names = page.evaluate("caches.keys()")
        has_v85 = any("v85-tech-metadata" in name for name in cache_names)

        page.screenshot(path=str(OUT / "pwa-v85-mobile-390x844.png"))
        mobile = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "pwa-v85-desktop-1440x1000.png"))
        desktop = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})")

        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "result": "PASS" if has_v85 and not errors and mobile["document"] <= mobile["viewport"] and desktop["document"] <= desktop["viewport"] else "FAIL",
            "url": BASE_URL,
            "http_status": response.status,
            "service_worker_controller": sw_version,
            "active_cache_names": cache_names,
            "v85_cache_active": has_v85,
            "mobile_390x844": mobile,
            "desktop_1440x1000": desktop,
            "page_and_console_errors": errors,
            "screenshots": ["pwa-v85-mobile-390x844.png", "pwa-v85-desktop-1440x1000.png"],
            "isolation": "Fresh isolated Chrome context; application demo data only; no user browser profile attached.",
        }
        (OUT / "pwa-smoke-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        browser.close()
        if result["result"] != "PASS":
            raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))
        print("PASS: PWA v85 update, mobile/desktop width smoke, zero browser errors; screenshots saved.")


if __name__ == "__main__":
    main()
