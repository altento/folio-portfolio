from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"


def inspect_controls(page) -> dict:
    return page.evaluate("""() => {
      const visible = el => !!(el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');
      const controls = [...document.querySelectorAll('a,button,input,select,textarea,[role=button],[tabindex]')]
        .filter(el => visible(el) && !el.matches('[tabindex="-1"]') && el.type !== 'hidden');
      const named = el => {
        const ids = (el.getAttribute('aria-labelledby') || '').split(/\\s+/).filter(Boolean);
        const labelled = ids.map(id => document.getElementById(id)?.innerText || '').join(' ');
        const labels = el.labels ? [...el.labels].map(label => label.innerText).join(' ') : '';
        return (el.getAttribute('aria-label') || labelled || labels || el.innerText || el.value || el.getAttribute('title') || '').trim();
      };
      const missingNames = controls.filter(el => !named(el)).map(el => ({tag:el.tagName,id:el.id,type:el.type,role:el.getAttribute('role')}));
      const fields = [...document.querySelectorAll('input:not([type=hidden]),select,textarea')]
        .filter(el => visible(el) && !el.matches('[tabindex="-1"]') && !el.closest('[aria-hidden="true"]') && !['submit','button','reset'].includes(el.type));
      const missingFieldLabels = fields.filter(el => !(el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || (el.labels && el.labels.length)))
        .map(el => ({name:el.name,id:el.id,type:el.type,placeholder:el.placeholder}));
      const missingImageAlt = [...document.images].filter(img => visible(img) && !img.hasAttribute('alt')).map(img => img.src);
      return {controlCount:controls.length,missingNames,fieldCount:fields.length,missingFieldLabels,visibleImageCount:[...document.images].filter(visible).length,missingImageAlt};
    }""")


def main() -> None:
    errors: list[str] = []
    views: dict[str, dict] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="allow")
        page = context.new_page()
        page.set_default_timeout(8_000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        response = page.goto(URL, wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise AssertionError("PWA did not load successfully.")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "a11y-v93-mobile-dashboard.png"))
        views["dashboard_mobile_390x844"] = inspect_controls(page)

        opener = page.locator('[data-action="new-project"]:visible').first
        opener.click()
        page.wait_for_function("document.querySelector('#project-dialog-title')?.textContent.includes('Новый проект')")
        title = page.locator('#project-form [name="title"]')
        if not title.evaluate("el => document.activeElement === el"):
            raise AssertionError("New-project dialog did not focus its first required field.")
        dialog_name = page.locator('#project-dialog').get_attribute('aria-labelledby')
        if not dialog_name or not page.locator(f'#{dialog_name}').count():
            raise AssertionError("Project dialog does not expose its labelled heading.")
        views["new_project_dialog_mobile"] = inspect_controls(page)
        page.screenshot(path=str(OUT / "a11y-v93-mobile-project-dialog.png"))

        page.keyboard.press("Tab")
        tab_sequence = []
        focus_states = set()
        for _ in range(45):
            state = page.evaluate("""() => {
              const el=document.activeElement;
              return {inside:!!el.closest('#project-dialog'),tag:el.tagName,id:el.id,name:el.getAttribute('name'),aria:el.getAttribute('aria-label'),text:(el.innerText||'').trim().slice(0,40)};
            }""")
            key = json.dumps(state, sort_keys=True)
            tab_sequence.append(state)
            if not state["inside"]:
                raise AssertionError(f"Tab focus escaped the modal dialog: {state}")
            if key in focus_states and len(focus_states) > 6:
                break
            focus_states.add(key)
            page.keyboard.press("Tab")

        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('#project-dialog').open")
        focus_returned = page.evaluate("el => document.activeElement === el", opener.element_handle())
        if not focus_returned:
            raise AssertionError("Escape did not return focus to the project-dialog opener.")

        opener.click()
        page.wait_for_function("document.querySelector('#project-dialog')?.open")
        page.locator('#project-form button[type="submit"]').click()
        invalid_fields = page.locator('#project-form :invalid').evaluate_all("els => els.map(el=>el.name)")
        if not {"title", "description"}.issubset(set(invalid_fields)):
            raise AssertionError(f"Required project fields are not exposed as invalid: {invalid_fields}")
        invalid_focus = page.evaluate("document.activeElement?.name")
        page.keyboard.press("Escape")

        page.emulate_media(reduced_motion="reduce")
        motion = page.evaluate("""() => {
          const el=document.querySelector('.project-card .cover-image') || document.querySelector('main');
          const style=getComputedStyle(el);
          return {transitionDuration:style.transitionDuration,animationName:style.animationName,scrollBehavior:getComputedStyle(document.documentElement).scrollBehavior};
        }""")

        for name, key in [("projects_mobile_390x844", "projects"), ("showcase_mobile_390x844", "showcase"), ("settings_mobile_390x844", "settings")]:
            page.locator(f'[data-view="{key}"]:visible').first.click()
            page.wait_for_timeout(150)
            views[name] = inspect_controls(page)
        page.set_viewport_size({"width": 320, "height": 568})
        page.wait_for_timeout(150)
        views["settings_mobile_320x568"] = inspect_controls(page)
        mobile_width_320 = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})")
        page.set_viewport_size({"width": 390, "height": 844})
        mobile_widths = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})")

        page.set_viewport_size({"width": 1440, "height": 1000})
        page.locator('[data-view="projects"]:visible').first.click()
        page.wait_for_timeout(200)
        views["projects_desktop_1440x1000"] = inspect_controls(page)
        desktop_widths = page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})")
        page.screenshot(path=str(OUT / "a11y-v93-desktop-projects.png"))
        page.locator('[data-view="settings"]:visible').first.click()
        page.wait_for_timeout(200)
        views["settings_desktop_1440x1000"] = inspect_controls(page)

        failures = []
        for view_name, report in views.items():
            if report["missingNames"]:
                failures.append(f"{view_name}: controls without names {report['missingNames']}")
            if report["missingFieldLabels"]:
                failures.append(f"{view_name}: form fields without labels {report['missingFieldLabels']}")
            if report["missingImageAlt"]:
                failures.append(f"{view_name}: visible images without alt attributes {report['missingImageAlt']}")
        if mobile_widths["document"] > mobile_widths["viewport"] or desktop_widths["document"] > desktop_widths["viewport"] or mobile_width_320["document"] > mobile_width_320["viewport"]:
            failures.append("Horizontal overflow detected.")
        if motion["animationName"] != "none" or motion["scrollBehavior"] != "auto":
            failures.append(f"Reduced-motion preferences were not respected: {motion}")
        if errors:
            failures.append(f"Browser errors: {errors}")

        result = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "result": "PASS" if not failures else "FAIL",
            "scope": "Isolated Chrome functional accessibility smoke; not a full WCAG audit or assistive-technology test.",
            "views": views,
            "dialog": {"aria_labelledby": dialog_name, "initial_focus": "title", "tab_sequence_length": len(tab_sequence), "tab_focus_trapped": True, "escape_focus_return": focus_returned},
            "empty_form_validation": {"invalid_fields": invalid_fields, "focus_after_submit": invalid_focus},
            "reduced_motion": motion,
            "mobile_390x844": mobile_widths,
            "desktop_1440x1000": desktop_widths,
            "mobile_320x568": mobile_width_320,
            "page_and_console_errors": errors,
            "failures": failures,
            "screenshots": ["a11y-v93-mobile-dashboard.png", "a11y-v93-mobile-project-dialog.png", "a11y-v93-desktop-projects.png"],
        }
        (OUT / "a11y-keyboard-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        browser.close()
        if failures:
            raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))
        print("PASS: accessible names/labels, modal keyboard path, required-field feedback, reduced motion, widths; screenshots saved.")


if __name__ == "__main__":
    main()


