from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
URL = os.environ.get("FOLIO_AUDIT_URL", "http://127.0.0.1:41803/")
CHROME = Path(os.environ.get("FOLIO_CHROME_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
VIEWPORTS = ((320, 568), (390, 568), (390, 844), (768, 900), (1440, 900))
ROUTES = ("dashboard", "projects", "showcase", "settings")


async def wait_projects(page, count: int) -> None:
    await page.wait_for_function(
        "expected => document.querySelectorAll('.project-card').length === expected",
        arg=count,
        timeout=10000,
    )


async def goto_route(page, route: str) -> None:
    await page.locator(f'[data-view="{route}"]:visible').first.click()
    await page.locator("#main-content h1").first.wait_for(state="visible")
    await page.wait_for_timeout(120)


async def main() -> None:
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    route_matrix: list[dict] = []
    evidence: list[dict] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path=str(CHROME))
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
        )
        page = await context.new_page()
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
        response = await page.goto(URL, wait_until="networkidle")
        await page.wait_for_function(
            "document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'",
            timeout=20000,
        )
        await page.locator("#main-content h1").first.wait_for(state="visible")
        await wait_projects(page, 3)
        insight_badge = (await page.locator(".insight-count").first.inner_text()).strip()

        await goto_route(page, "projects")
        disclosures_closed = await page.evaluate("""() => {
          const filter = document.querySelector('#project-filter-disclosure');
          const filterBody = filter?.querySelector('.filter-disclosure-body');
          const saved = document.querySelector('#saved-views-disclosure');
          const savedBody = saved?.querySelector('.saved-views');
          const measure = element => ({
            display: element ? getComputedStyle(element).display : null,
            clientRects: element?.getClientRects().length ?? 0,
            visibleControls: [...(element?.querySelectorAll('select,input,button') || [])]
              .filter(control => control.getClientRects().length > 0).length
          });
          return {
            filterOpen: Boolean(filter?.open),
            filterBody: measure(filterBody),
            savedViewsOpen: Boolean(saved?.open),
            savedViewsBody: measure(savedBody)
          };
        }""")
        await page.locator("#project-filter-disclosure > summary").click()
        await page.locator("#project-filter-disclosure .filter-disclosure-body").wait_for(state="visible")
        visible_filter_controls = {
            name: await page.get_by_role(role, name=name).count()
            for role, name in (
                ("combobox", "Тип"),
                ("combobox", "Статус"),
                ("combobox", "Тег"),
                ("combobox", "Сортировка проектов"),
                ("checkbox", "Только избранное"),
            )
        }
        disclosure_screenshot = OUTPUT / "project-filters-open-390x844.png"
        await page.screenshot(path=str(disclosure_screenshot), full_page=True)
        evidence.append({"file": disclosure_screenshot.name, "sha256": hashlib.sha256(disclosure_screenshot.read_bytes()).hexdigest()})
        await page.locator("#project-filter-disclosure > summary").click()
        await page.locator("#saved-views-disclosure > summary").click()
        await page.locator("#saved-views-disclosure .saved-views").wait_for(state="visible")
        saved_view_controls = {
            "selector": await page.get_by_role("combobox", name="Сохранённые представления").count(),
            "save": await page.get_by_role("button", name="Сохранить вид").count(),
            "delete": await page.get_by_role("button", name="Удалить выбранное представление").count(),
        }
        await page.locator("#saved-views-disclosure > summary").click()
        disclosure_open_result = {
            "filter_controls_by_accessible_name": visible_filter_controls,
            "saved_view_controls_by_accessible_name": saved_view_controls,
        }
        if disclosures_closed["filterOpen"] or disclosures_closed["savedViewsOpen"]:
            raise RuntimeError("Mobile filter and saved-view disclosures should start closed.")
        if any(value["display"] != "none" or value["clientRects"] != 0 or value["visibleControls"] != 0
               for value in (disclosures_closed["filterBody"], disclosures_closed["savedViewsBody"])):
            raise RuntimeError("A closed mobile disclosure still exposes visible child controls.")
        if any(count != 1 for count in visible_filter_controls.values()) or any(count != 1 for count in saved_view_controls.values()):
            raise RuntimeError("An opened mobile disclosure control has an unexpected accessible name.")

        for width, height in VIEWPORTS:
            await page.set_viewport_size({"width": width, "height": height})
            await page.wait_for_timeout(120)
            for route in ROUTES:
                await goto_route(page, route)
                record = await page.evaluate("""() => {
                  const visible = element => element && element.getClientRects().length > 0;
                  const main = document.querySelector('#main-content');
                  const title = document.querySelector('#main-content h1');
                  const actionable = [...main.querySelectorAll('button, a, input, select, textarea')].filter(visible);
                  const touchTargets = actionable.map(element => {
                    const target = element.matches('input[type="checkbox"]') ? (element.closest('label') || element) : element;
                    const rect = target.getBoundingClientRect();
                    return {element, target, height: Math.round(rect.height), width: Math.round(rect.width)};
                  });
                  const images = [...main.querySelectorAll('.project-card img')].filter(visible);
                  const readabilityLabels = [...main.querySelectorAll(
                    '.portfolio-insights .eyebrow, .portfolio-insights .insight-count, .editorial-stat-grid .stat-card>span, .project-card .tag-row i'
                  )].filter(visible);
                  const readabilityFonts = readabilityLabels.map(element => parseFloat(getComputedStyle(element).fontSize));
                  return {
                    viewport: [innerWidth, innerHeight],
                    title: title?.innerText.trim() || '',
                    documentWidth: document.documentElement.scrollWidth,
                    bodyWidth: document.body.scrollWidth,
                    projectCards: document.querySelectorAll('.project-card').length,
                    visibleProjectImages: images.length,
                    brokenProjectImages: images.filter(image => image.complete && image.naturalWidth === 0).length,
                    visibleControls: actionable.length,
                    smallestControlHeight: actionable.length ? Math.min(...actionable.map(el => Math.round(el.getBoundingClientRect().height))) : null,
                    smallestTouchTargetHeight: touchTargets.length ? Math.min(...touchTargets.map(target => target.height)) : null,
                    touchTargetsBelow44: touchTargets.filter(target => target.height < 44).map(target => ({
                      tag: target.element.tagName,
                      className: String(target.element.className || ''),
                      labelClass: target.element.matches('input[type="checkbox"]') ? String(target.target.className || '') : '',
                      text: (target.element.innerText || target.element.getAttribute('aria-label') || '').trim().slice(0, 60),
                      height: target.height,
                      width: target.width
                    })),
                    mobileReadability: readabilityFonts.length ? {
                      measuredLabels: readabilityFonts.length,
                      smallestFontPx: Math.min(...readabilityFonts),
                      below10px: readabilityFonts.filter(size => size < 10).length
                    } : null,
                    mainHeight: Math.round(main.getBoundingClientRect().height)
                  };
                }""")
                record["route"] = route
                record["noHorizontalOverflow"] = record["documentWidth"] <= width and record["bodyWidth"] <= width
                route_matrix.append(record)
                if width == 390 and height == 844 and route in ("dashboard", "projects", "settings"):
                    await page.evaluate("""async () => {
                      const images = [...document.querySelectorAll('#main-content .project-card img')];
                      for (const image of images) image.loading = 'eager';
                      await Promise.all(images.map(image => image.decode().catch(() => undefined)));
                    }""")
                    screenshot = OUTPUT / f"{route}-390x844.png"
                    await page.screenshot(path=str(screenshot), full_page=True)
                    evidence.append({"file": screenshot.name, "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()})
                    viewport_screenshot = OUTPUT / f"{route}-390x844-viewport.png"
                    await page.screenshot(path=str(viewport_screenshot), full_page=False)
                    evidence.append({"file": viewport_screenshot.name, "sha256": hashlib.sha256(viewport_screenshot.read_bytes()).hexdigest()})
                if width == 1440 and height == 900 and route in ("dashboard", "projects"):
                    screenshot = OUTPUT / f"{route}-1440x900.png"
                    await page.screenshot(path=str(screenshot), full_page=False)
                    evidence.append({"file": screenshot.name, "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()})

        await page.set_viewport_size({"width": 390, "height": 844})
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("Boolean(navigator.serviceWorker?.controller)", timeout=15000)
        await context.set_offline(True)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'", timeout=15000)
        await page.locator("#main-content h1").first.wait_for(state="visible")
        await wait_projects(page, 3)
        await page.evaluate("""async () => {
          const images = [...document.querySelectorAll('#main-content .project-card img')];
          for (const image of images) image.loading = 'eager';
          await Promise.all(images.map(image => image.decode().catch(() => undefined)));
        }""")
        offline = await page.evaluate("""() => ({
          controller: Boolean(navigator.serviceWorker?.controller),
          online: navigator.onLine,
          projectCount: document.querySelectorAll('.project-card').length,
          title: document.querySelector('#main-content h1')?.innerText.trim() || '',
          brokenImages: [...document.querySelectorAll('#main-content .project-card img')].filter(image => image.complete && image.naturalWidth === 0).length
        })""")
        offline_screenshot = OUTPUT / "offline-dashboard-390x844.png"
        await page.screenshot(path=str(offline_screenshot), full_page=True)
        evidence.append({"file": offline_screenshot.name, "sha256": hashlib.sha256(offline_screenshot.read_bytes()).hexdigest()})
        offline_viewport_screenshot = OUTPUT / "offline-dashboard-390x844-viewport.png"
        await page.screenshot(path=str(offline_viewport_screenshot), full_page=False)
        evidence.append({"file": offline_viewport_screenshot.name, "sha256": hashlib.sha256(offline_viewport_screenshot.read_bytes()).hexdigest()})
        await context.set_offline(False)

        # Use a fresh isolated browser context for the complete create/edit/delete flow.
        await page.set_viewport_size({"width": 390, "height": 844})
        await goto_route(page, "projects")
        project_name = "QA·«Folio smoke»"
        await page.locator('[data-action="new-project"]:visible').first.click()
        await page.locator("#project-dialog[open]").wait_for()
        await page.locator('#project-form [name="title"]').fill(project_name)
        await page.locator('#project-form [name="description"]').fill("Синтетическая запись для проверки адаптивной формы и сохранения.")
        wizard_visible = await page.locator("#project-form-wizard").is_visible()
        if wizard_visible:
            for _ in range(2):
                await page.locator("#project-form-step-next").click()
                await page.wait_for_timeout(80)
        await page.locator("#project-form-submit").click()
        await page.locator("#project-dialog[open]").wait_for(state="hidden")
        await goto_route(page, "projects")
        await page.get_by_text(project_name, exact=True).wait_for()
        await wait_projects(page, 4)

        await page.reload(wait_until="networkidle")
        await page.locator("#main-content h1").first.wait_for(state="visible")
        await goto_route(page, "projects")
        await page.get_by_text(project_name, exact=True).wait_for()
        await wait_projects(page, 4)

        card_button = page.locator(".project-card").filter(has_text=project_name).locator("[data-detail]")
        await card_button.click()
        await page.locator("#detail-dialog[open]").wait_for()
        await page.locator("#detail-dialog [data-edit]").click()
        await page.locator("#project-dialog[open]").wait_for()
        await page.locator('#project-form [name="description"]').fill("Описание изменено в синтетическом edit-сценарии.")
        if await page.locator("#project-form-wizard").is_visible():
            for _ in range(2):
                await page.locator("#project-form-step-next").click()
                await page.wait_for_timeout(80)
        await page.locator("#project-form-submit").click()
        await page.locator("#project-dialog[open]").wait_for(state="hidden")
        await goto_route(page, "projects")
        await page.locator(".project-card").filter(has_text=project_name).get_by_text("Описание изменено в синтетическом edit-сценарии.").wait_for()

        await page.locator(".project-card").filter(has_text=project_name).locator("[data-detail]").click()
        await page.locator("#detail-dialog[open]").wait_for()
        await page.locator("#detail-dialog [data-delete]").click()
        undo_button = page.get_by_role("button", name="Отменить", exact=True)
        await undo_button.wait_for(state="visible", timeout=4000)
        await undo_button.click()
        await wait_projects(page, 4)
        await page.locator(".project-card").filter(has_text=project_name).locator("[data-detail]").click()
        await page.locator("#detail-dialog[open]").wait_for()
        await page.locator("#detail-dialog [data-delete]").click()
        await page.wait_for_timeout(7400)
        await wait_projects(page, 3)
        crud = {
            "wizard_visible_on_mobile": wizard_visible,
            "create_project_persisted_after_reload": True,
            "edit_project_visible_in_card": True,
            "undo_delete_restored_project": True,
            "recoverable_delete_expired_and_restored_demo_count": 3,
            "synthetic_project_name": project_name,
        }
        await browser.close()

    result = {
        "date": datetime.now().date().isoformat(),
    "candidate_versions": {"web": "v161", "windows": "v164", "android": "0.3.24/code36"},
        "url": URL,
        "http_status": response.status if response else None,
        "browser": "Installed Chrome, isolated Playwright context",
        "viewports": list(VIEWPORTS),
        "route_matrix": route_matrix,
        "dashboard_insight_badge": insight_badge,
        "mobile_disclosures_closed": disclosures_closed,
        "mobile_disclosures_open_controls": disclosure_open_result,
        "offline_cold_reload": offline,
        "crud_flow": crud,
        "browser_errors": errors,
        "screenshots": evidence,
        "data_scope": "fresh isolated browser context; no user profile or existing database used",
    }
    (OUTPUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    failures = [row for row in route_matrix if not row["noHorizontalOverflow"]]
    small_targets = [row for row in route_matrix if row["touchTargetsBelow44"]]
    readability_failures = [
        row for row in route_matrix
        if row["viewport"][0] <= 390
        and row["mobileReadability"] is not None
        and row["mobileReadability"]["below10px"]
    ]
    if response is None or response.status != 200 or errors or failures or small_targets or readability_failures or offline["online"] or not offline["controller"] or offline["projectCount"] != 3 or offline["brokenImages"] or "1 подсказка" not in insight_badge or "1 1" in insight_badge or not crud["create_project_persisted_after_reload"] or not crud["wizard_visible_on_mobile"]:
        raise SystemExit("Current product smoke failed")


if __name__ == "__main__":
    asyncio.run(main())


