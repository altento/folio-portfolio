from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright


OUT = Path(__file__).resolve().parent
URL = os.environ.get("FOLIO_AUDIT_URL", "http://127.0.0.1:8765/")
CHROME = Path(os.environ.get("FOLIO_CHROME_EXECUTABLE", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
AXE_VERSION = "4.14.0"
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]


def get_axe_script(temp: Path) -> Path:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is not available in PATH for the pinned axe-core audit")
    packed = subprocess.run(
        [npm, "pack", f"axe-core@{AXE_VERSION}", "--pack-destination", str(temp)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        shell=(os.name == "nt"),
    )
    tarball = temp / packed.stdout.strip().splitlines()[-1]
    with tarfile.open(tarball, "r:gz") as archive:
        member = archive.extractfile("package/axe.min.js")
        if member is None:
            raise RuntimeError("Pinned axe-core package is missing axe.min.js")
        script = temp / "axe.min.js"
        script.write_bytes(member.read())
    return script


async def main() -> None:
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    observations: list[dict] = []
    screenshots: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="folio-update-axe-") as raw_temp:
        axe_script = get_axe_script(Path(raw_temp))
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
            await page.add_script_tag(path=str(axe_script))

            for width, height, label in ((390, 844, "mobile"), (1440, 900, "desktop")):
                await page.set_viewport_size({"width": width, "height": height})
                notice = page.locator("#update-notice")
                await notice.evaluate("element => { element.hidden = false; }")
                await page.wait_for_timeout(100)
                scan = await page.evaluate(
                    """async tags => {
                      const result = await axe.run(document, {runOnly: {type: 'tag', values: tags}});
                      return {
                        violationCount: result.violations.length,
                        violations: result.violations.map(item => ({id: item.id, impact: item.impact, targets: item.nodes.map(node => node.target)})),
                        incompleteRules: result.incomplete.map(item => item.id),
                        statusRoleViolations: result.violations.filter(item => item.id === 'aria-allowed-role').length,
                        statusRoleReview: result.incomplete.filter(item => item.id === 'aria-allowed-role').length,
                      };
                    }""",
                    AXE_TAGS,
                )
                geometry = await notice.evaluate(
                    """element => {
                      const box = element.getBoundingClientRect();
                      const message = element.querySelector('[role=status]');
                      const messageBox = message.getBoundingClientRect();
                      return {
                        visible: !element.hidden,
                        role: element.getAttribute('role'),
                        name: document.getElementById(element.getAttribute('aria-labelledby'))?.textContent.trim(),
                        messageRole: message?.getAttribute('role'),
                        messageText: message?.innerText.trim(),
                        messageContainsInteractiveControl: Boolean(message?.querySelector('button,a,input,select,textarea,[tabindex]')),
                        buttonNames: [...element.querySelectorAll('button')].map(button => button.getAttribute('aria-label') || button.innerText.trim()),
                        box: {x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height)},
                        messageBox: {width: Math.round(messageBox.width), height: Math.round(messageBox.height)},
                      };
                    }"""
                )
                screenshot = OUT / f"update-notice-{label}-v153.png"
                await page.screenshot(path=str(screenshot), full_page=False)
                screenshots.append({"file": screenshot.name, "width": width, "height": height, "sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest()})
                dismissed = False
                if await page.get_by_role("button", name="Скрыть уведомление").count() == 1:
                    await page.get_by_role("button", name="Скрыть уведомление").click()
                    dismissed = await notice.evaluate("element => element.hidden")
                observations.append({"viewport": [width, height], "label": label, "geometry": geometry, "axe": scan, "dismissActionHidesNotice": dismissed})

            await browser.close()

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "url": URL,
        "http_status": response.status if response else None,
        "browser": "Installed Chrome, isolated Playwright context",
        "axe_core_version": AXE_VERSION,
        "axe_tags": AXE_TAGS,
        "observations": observations,
        "page_and_console_errors": errors,
        "screenshots": screenshots,
        "data_scope": "fresh isolated browser context; no user profile or stored portfolio used",
        "limits": ["Automated axe checks and DOM geometry do not replace TalkBack, Narrator, or physical-device acceptance."],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if response is None or response.status != 200 or errors:
        raise SystemExit("Update notice browser smoke failed")
    for observation in observations:
        if observation["axe"]["violationCount"] or observation["axe"]["statusRoleReview"] or not observation["dismissActionHidesNotice"]:
            raise SystemExit(f"Update notice accessibility review failed for {observation['label']}")


if __name__ == "__main__":
    asyncio.run(main())
