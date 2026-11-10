import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

AUDIT_CONTROLS = """() => {
  const visible = element => Boolean(element.getClientRects().length &&
    getComputedStyle(element).visibility !== 'hidden' &&
    !element.closest('[aria-hidden=true]'));
  const name = element => {
    const references = (element.getAttribute('aria-labelledby') || '')
      .split(/\\s+/).filter(Boolean)
      .map(id => document.getElementById(id)?.innerText || '').join(' ').trim();
    const labels = element.labels
      ? [...element.labels].map(label => label.innerText || label.textContent || '').join(' ').trim()
      : '';
    const text = (element.innerText || element.textContent || '').trim();
    const imageAlt = [...element.querySelectorAll('img')]
      .map(image => image.alt).filter(Boolean).join(' ');
    return element.getAttribute('aria-label') || references || labels || text ||
      imageAlt || element.getAttribute('title') || element.getAttribute('placeholder') || '';
  };
  const controls = [...document.querySelectorAll(
    'button,a[href],input:not([type=hidden]),select,textarea,[role=button]'
  )].filter(visible);
  const images = [...document.querySelectorAll('img')].filter(visible);
  return {
    title: document.title,
    lang: document.documentElement.lang,
    mainCount: document.querySelectorAll('main').length,
    navCount: document.querySelectorAll('nav').length,
    headings: [...document.querySelectorAll('h1')].map(node => node.innerText),
    visibleControlCount: controls.length,
    controlsWithoutDetectedName: controls.filter(element => !name(element)).map(element => ({
      tag: element.tagName.toLowerCase(),
      type: element.getAttribute('type'),
      id: element.id,
      role: element.getAttribute('role')
    })),
    visibleImagesWithoutAlt: images.filter(image => !image.hasAttribute('alt'))
      .map(image => image.src)
  };
}"""

async def main():
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {"url": URL, "viewport": [390, 844], "routes": [], "keyboard": {},
              "project_form": {}, "browser_errors": []}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, executable_path=str(CHROME)
        )
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        page.on("pageerror", lambda error: result["browser_errors"].append(str(error)))
        page.on("console", lambda message:
                result["browser_errors"].append(message.text)
                if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle", timeout=20000)
        result["http_status"] = response.status if response else None
        await page.wait_for_function(
            "document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'",
            timeout=15000
        )
        await page.keyboard.press("Tab")
        result["keyboard"]["first_tab"] = await page.evaluate(
            "() => ({className:document.activeElement?.className, "
            "text:(document.activeElement?.innerText||'').trim(), "
            "href:document.activeElement?.getAttribute('href')})"
        )
        await page.keyboard.press("Enter")
        result["keyboard"]["skip_target_active"] = await page.evaluate(
            "document.activeElement?.id === 'main-content'"
        )

        for route in ("dashboard", "projects", "showcase", "settings"):
            await page.locator(f'[data-view="{route}"]:visible').first.click()
            await page.locator("#main-content h1").first.wait_for(state="visible")
            if route == "projects":
                for selector in (
                    "#project-filter-disclosure summary",
                    "#saved-views-disclosure summary"
                ):
                    parent = page.locator(selector).locator("..")
                    if not await parent.get_attribute("open"):
                        await page.locator(selector).click()
                await page.screenshot(
                    path=str(OUTPUT / "projects-filters-open-390x844.png"),
                    full_page=True
                )
            route_result = await page.evaluate(AUDIT_CONTROLS)
            result["routes"].append({"route": route, **route_result})

        trigger = page.locator('button[data-action="new-project"]:visible').first
        await trigger.evaluate("(element) => { element.id = 'qa-dialog-trigger'; }")
        await trigger.click()
        await page.locator("#project-dialog[open]").wait_for(state="visible")
        result["project_form"] = await page.evaluate("""() => {
          const dialog = document.querySelector('#project-dialog');
          const controls = [...dialog.querySelectorAll(
            'input:not([type=hidden]),select,textarea,button'
          )].filter(element => element.getClientRects().length &&
            getComputedStyle(element).visibility !== 'hidden');
          const hasName = element => Boolean(
            element.getAttribute('aria-label') ||
            (element.getAttribute('aria-labelledby') || '').split(/\\s+/)
              .filter(Boolean).map(id => document.getElementById(id)?.textContent || '')
              .join(' ').trim() ||
            (element.labels && [...element.labels]
              .map(label => label.textContent || '').join(' ').trim()) ||
            element.innerText?.trim() || element.textContent?.trim() ||
            element.title || element.placeholder
          );
          return {
            role: dialog.getAttribute('role') || 'dialog',
            labelledby: dialog.getAttribute('aria-labelledby'),
            title: document.getElementById(
              dialog.getAttribute('aria-labelledby')
            )?.innerText,
            initialFocusId: document.activeElement?.id,
            visibleControlCount: controls.length,
            controlsWithoutDetectedName: controls.filter(element => !hasName(element))
              .map(element => ({
                tag: element.tagName,
                type: element.type,
                id: element.id,
                name: element.name
              }))
          };
        }""")
        await page.screenshot(
            path=str(OUTPUT / "new-project-dialog-390x844.png"),
            full_page=False
        )
        await page.keyboard.press("Escape")
        result["keyboard"]["escape_closed_dialog"] = await page.evaluate(
            "!document.querySelector('#project-dialog').open"
        )
        result["keyboard"]["focus_returned_to_actual_trigger"] = await page.evaluate(
            "document.activeElement?.id === 'qa-dialog-trigger'"
        )
        await browser.close()

    result["checks"] = {
        "http_200": result["http_status"] == 200,
        "skip_link_is_first_tab_stop": result["keyboard"]["first_tab"]["className"] == "skip-link",
        "skip_link_moves_focus_to_main": result["keyboard"]["skip_target_active"] is True,
        "all_four_routes_have_no_controls_without_detected_name": all(
            not route["controlsWithoutDetectedName"] for route in result["routes"]
        ),
        "all_four_routes_have_no_visible_images_without_alt": all(
            not route["visibleImagesWithoutAlt"] for route in result["routes"]
        ),
        "project_dialog_has_accessible_title": bool(
            result["project_form"]["labelledby"] and result["project_form"]["title"]
        ),
        "project_form_controls_have_detected_names": not
            result["project_form"]["controlsWithoutDetectedName"],
        "escape_closes_dialog": result["keyboard"]["escape_closed_dialog"] is True,
        "focus_returns_to_actual_trigger":
            result["keyboard"]["focus_returned_to_actual_trigger"] is True,
        "browser_errors_zero": not result["browser_errors"]
    }
    result["all_checks_passed"] = all(result["checks"].values())
    (OUTPUT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result["all_checks_passed"]:
        raise SystemExit(1)

asyncio.run(main())
