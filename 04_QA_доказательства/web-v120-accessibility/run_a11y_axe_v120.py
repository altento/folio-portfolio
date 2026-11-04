from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8777/"
AXE_VERSION = "4.14.0"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]


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


def summarize(result: dict) -> dict:
    return {
        "violation_count": len(result["violations"]),
        "violations": [
            {
                "id": item["id"],
                "impact": item["impact"],
                "help": item["help"],
                "help_url": item["helpUrl"],
                "nodes": [
                    {"target": node["target"], "failure_summary": node["failureSummary"]}
                    for node in item["nodes"]
                ],
            }
            for item in result["violations"]
        ],
        "incomplete_count": len(result["incomplete"]),
        "incomplete_rules": sorted({item["id"] for item in result["incomplete"]}),
        "incomplete_review_targets": [
            {
                "rule": item["id"],
                "nodes": [
                    {
                        "target": node["target"],
                        "checks": [
                            {"id": check["id"], "message": check["message"]}
                            for group in ("any", "all", "none")
                            for check in node.get(group, [])
                        ],
                    }
                    for node in item.get("nodes", [])
                ],
            }
            for item in result["incomplete"]
        ],
        "passes_count": len(result["passes"]),
    }


def main() -> None:
    page_errors: list[str] = []
    scans: dict[str, dict] = {}
    screenshots: list[str] = []
    with tempfile.TemporaryDirectory(prefix="folio-axe-v120-") as raw_temp:
        axe_script = get_axe_script(Path(raw_temp))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                headless=True,
            )
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                service_workers="allow",
            )
            page = context.new_page()
            page.set_default_timeout(10_000)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: page_errors.append(message.text) if message.type == "error" else None)
            response = page.goto(URL, wait_until="networkidle", timeout=30_000)
            if response is None or response.status != 200:
                raise AssertionError("PWA did not load successfully")
            page.wait_for_timeout(1_000)  # The isolated audit checks semantics; service worker lifecycle is covered by separate offline QA.
            page.add_script_tag(path=str(axe_script))
            axe_run = """async tags => {
              const r=await axe.run(document,{runOnly:{type:'tag',values:tags}});
              return {version:axe.version,violations:r.violations,incomplete:r.incomplete,passes:r.passes};
            }"""

            def scan(name: str) -> None:
                scans[name] = summarize(page.evaluate(axe_run, TAGS))

            def capture(name: str) -> None:
                filename = f"axe-v120-{name}.png"
                page.screenshot(path=str(OUT / filename), full_page=True)
                screenshots.append(filename)

            scan("dashboard_mobile_light_390")
            capture("dashboard-mobile-light-390")

            page.locator(".mobile-nav-item[data-view='projects']").click()
            scan("projects_mobile_light_390")
            capture("projects-mobile-light-390")
            page.set_viewport_size({"width": 320, "height": 568})
            scan("projects_mobile_light_320")
            capture("projects-mobile-light-320")

            page.locator("[data-detail]:visible").first.click()
            page.locator("#detail-dialog[open]").wait_for()
            scan("detail_mobile_light_320")
            page.keyboard.press("Escape")

            page.locator("[data-action='new-project']:visible").first.click()
            page.locator("#project-dialog[open]").wait_for()
            page.locator("#project-dialog [name=title]").fill("Accessibility audit case")
            page.locator("#project-dialog [name=description]").fill("Temporary data for editor accessibility review.")
            scan("project_editor_step_1_mobile_320")
            capture("project-editor-step-1-mobile-320")
            page.locator("#project-form-step-next").click()
            scan("project_editor_step_2_mobile_320")
            capture("project-editor-step-2-mobile-320")
            page.locator("#project-form-step-next").click()
            scan("project_editor_step_3_mobile_320")
            capture("project-editor-step-3-mobile-320")
            page.locator("#project-dialog [data-close-dialog]").first.click()

            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".mobile-nav-item[data-view='settings']").click()
            scan("settings_mobile_light_390")
            page.locator("#theme-toggle").click()
            scan("settings_mobile_dark_390")
            capture("settings-mobile-dark-390")
            page.locator(".mobile-nav-item[data-view='dashboard']").click()
            scan("dashboard_mobile_dark_390")
            page.set_viewport_size({"width": 1440, "height": 1000})
            scan("dashboard_desktop_dark_1440")
            capture("dashboard-desktop-dark-1440")
            page.locator("#theme-toggle").click()
            scan("dashboard_desktop_light_1440")

            page.locator(".nav-item[data-view='showcase']").click()
            scan("showcase_desktop_light_1440")
            page.locator("[data-action='preview-static']").click()
            page.locator("#showcase-preview-dialog[open]").wait_for()
            scan("showcase_preview_desktop_light_1440")
            page.locator("[data-preview-size='mobile']").click()
            scan("showcase_preview_mobile_light_390")
            capture("showcase-preview-mobile-390")

            caches = page.evaluate("async()=>await caches.keys()")
            browser.close()

    violation_total = sum(item["violation_count"] for item in scans.values())
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "axe_core_version": AXE_VERSION,
        "tags": TAGS,
        "url": URL,
        "service_worker_caches": caches,
        "result": "PASS" if violation_total == 0 and not page_errors else "REVIEW_REQUIRED",
        "scan_count": len(scans),
        "total_violations_across_scans": violation_total,
        "scans": scans,
        "page_and_console_errors": page_errors,
        "screenshots": screenshots,
        "limits": [
            "axe-core detects a subset of accessibility issues and does not certify WCAG conformance.",
            "No physical screen reader, switch control, direct browser zoom, or operating-system font scaling was tested.",
            "The project editor was scanned in all three mobile wizard steps; the temporary draft was not saved.",
        ],
    }
    (OUT / "axe-a11y-results-v120-local.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"axe-core {AXE_VERSION}: {result['result']}; {len(scans)} states, {violation_total} violations")
    if violation_total or page_errors:
        raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


