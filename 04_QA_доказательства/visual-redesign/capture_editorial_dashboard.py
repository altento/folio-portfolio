from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

output = Path(__file__).resolve().parent
base_url = os.environ.get("FOLIO_PREVIEW_URL", "http://127.0.0.1:8766/")
chrome = os.environ.get("CHROME_PATH") or shutil.which("chrome") or shutil.which("chrome.exe")
if not chrome:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    chrome = next((str(candidate) for candidate in candidates if candidate.is_file()), None)
if not chrome:
    raise SystemExit("Set CHROME_PATH or install Google Chrome to capture QA screenshots.")
results = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, executable_path=chrome, args=["--disable-extensions"])
    for label, width, height in [("desktop-1920x1080", 1920, 1080), ("mobile-390x844", 390, 844), ("mobile-320x568", 320, 568)]:
        context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1, is_mobile=width < 500, has_touch=width < 500)
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        response = page.goto(base_url, wait_until="networkidle", timeout=30000)
        page.locator(".dashboard-hero-editorial").wait_for(state="visible", timeout=10000)
        page.locator(".project-card").first.wait_for(state="visible", timeout=10000)
        page.wait_for_function("document.querySelector('.dashboard-hero-art')?.complete && document.querySelector('.dashboard-hero-art')?.naturalWidth > 0", timeout=10000)
        page.screenshot(path=str(output / f"folio-editorial-{label}.png"), full_page=False, animations="disabled")
        measurements = page.evaluate("""() => {
          const hero = document.querySelector('.dashboard-hero-editorial');
          const art = document.querySelector('.dashboard-hero-art');
          const topNew = document.querySelector('.topbar .top-actions > .top-new');
          return {
            viewportWidth: innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
            heroHeight: Math.round(hero.getBoundingClientRect().height),
            heroImageLoaded: art.complete && art.naturalWidth > 0,
            heroImageNaturalWidth: art.naturalWidth,
            topNewDisplay: topNew ? getComputedStyle(topNew).display : null,
            projectCards: document.querySelectorAll('.project-card').length,
            dashboardTitle: document.querySelector('.dashboard-hero h1')?.innerText
          };
        }""")
        results.append({"viewport": label, "http_status": response.status if response else None, **measurements, "page_errors": page_errors})
        context.close()
    browser.close()
(output / "folio-editorial-visual-check.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
