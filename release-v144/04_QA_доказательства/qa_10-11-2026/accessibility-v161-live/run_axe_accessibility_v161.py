import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
AXE = Path(__file__).resolve().parent / "axe-core-4.14.0" / "axe.min.js"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]

async def scan(page, state, results):
    raw = await page.evaluate("""async tags => {
      const result = await axe.run(document, {
        runOnly: {type: 'tag', values: tags}
      });
      return {
        violations: result.violations.map(rule => ({
          id: rule.id, impact: rule.impact, help: rule.help,
          helpUrl: rule.helpUrl,
          nodes: rule.nodes.map(node => ({
            target: node.target,
            summary: node.failureSummary
          }))
        })),
        incomplete: result.incomplete.map(rule => ({
          id: rule.id, impact: rule.impact, help: rule.help,
          nodeCount: rule.nodes.length,
          targets: rule.nodes.slice(0, 12).map(node => node.target)
        })),
        passes: result.passes.length,
        inapplicable: result.inapplicable.length
      };
    }""", TAGS)
    results.append({"state": state, **raw})

async def main():
    if not CHROME.is_file() or not AXE.is_file():
        raise FileNotFoundError(f"Chrome/Axe dependency not found: {CHROME} / {AXE}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {"date": "2026-11-10", "axe_version": "4.14.0", "url": URL,
              "viewport": [390, 844], "wcag_tags": TAGS, "states": [], "errors": []}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1, is_mobile=True, has_touch=True
        )
        page = await context.new_page()
        page.on("pageerror", lambda error: result["errors"].append(str(error)))
        page.on("console", lambda message:
                result["errors"].append(message.text) if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle", timeout=20000)
        result["http_status"] = response.status if response else None
        await page.wait_for_function(
            "document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'",
            timeout=15000
        )
        await page.add_script_tag(path=str(AXE))

        await scan(page, "mobile-dashboard-light", result["states"])
        await page.locator('[data-view="projects"]:visible').first.click()
        await page.locator("#main-content h1").wait_for(state="visible")
        await scan(page, "mobile-projects-filters-closed-light", result["states"])
        await page.locator("#project-filter-disclosure summary").click()
        await page.locator("#saved-views-disclosure summary").click()
        await scan(page, "mobile-projects-filters-and-saved-views-open-light", result["states"])
        await page.locator('button[data-action="new-project"]:visible').first.click()
        await page.locator("#project-dialog[open]").wait_for(state="visible")
        await scan(page, "mobile-new-project-dialog-light", result["states"])
        await page.keyboard.press("Escape")

        await page.locator('[data-view="showcase"]:visible').first.click()
        await page.locator("#main-content h1").wait_for(state="visible")
        await scan(page, "mobile-showcase-light", result["states"])
        await page.locator("[data-detail]").first.click()
        await page.locator("#detail-dialog[open]").wait_for(state="visible")
        await scan(page, "mobile-project-detail-dialog-light", result["states"])
        await page.keyboard.press("Escape")

        await page.locator('[data-view="settings"]:visible').first.click()
        await page.locator("#main-content h1").wait_for(state="visible")
        await scan(page, "mobile-settings-light", result["states"])
        await page.locator("#theme-toggle").click()
        result["dark_theme_active"] = await page.evaluate(
            "document.documentElement.dataset.theme === 'dark'"
        )
        await scan(page, "mobile-settings-dark", result["states"])
        await browser.close()

        desktop = await playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        desktop_context = await desktop.new_context(
            viewport={"width": 1440, "height": 900}, device_scale_factor=1
        )
        desktop_page = await desktop_context.new_page()
        desktop_page.on("pageerror", lambda error: result["errors"].append(str(error)))
        await desktop_page.goto(URL, wait_until="networkidle", timeout=20000)
        await desktop_page.wait_for_function(
            "document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'",
            timeout=15000
        )
        await desktop_page.add_script_tag(path=str(AXE))
        await scan(desktop_page, "desktop-dashboard-light", result["states"])
        await desktop_page.locator('[data-view="projects"]:visible').first.click()
        await desktop_page.locator("#main-content h1").wait_for(state="visible")
        await scan(desktop_page, "desktop-projects-light", result["states"])
        await desktop.close()

    result["violation_count"] = sum(len(state["violations"]) for state in result["states"])
    result["incomplete_count"] = sum(len(state["incomplete"]) for state in result["states"])
    result["all_scans_have_zero_violations"] = result["violation_count"] == 0
    result["browser_errors_zero"] = not result["errors"]
    (OUTPUT / "axe-core-4.14.0-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result["all_scans_have_zero_violations"] or not result["browser_errors_zero"]:
        raise SystemExit(1)

asyncio.run(main())
