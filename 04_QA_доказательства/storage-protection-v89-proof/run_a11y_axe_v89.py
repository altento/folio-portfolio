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
URL = "http://127.0.0.1:8766/"
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
                "nodes": [{"target": node["target"], "failure_summary": node["failureSummary"]} for node in item["nodes"]],
            }
            for item in result["violations"]
        ],
        "incomplete_count": len(result["incomplete"]),
        "incomplete_rules": sorted({item["id"] for item in result["incomplete"]}),
        "passes_count": len(result["passes"]),
    }


def main() -> None:
    page_errors: list[str] = []
    scans: dict[str, dict] = {}
    screenshots = []
    with tempfile.TemporaryDirectory(prefix="folio-axe-") as raw_temp:
        axe_script = get_axe_script(Path(raw_temp))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="allow")
            page = context.new_page()
            page.set_default_timeout(8_000)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: page_errors.append(message.text) if message.type == "error" else None)
            response = page.goto(URL, wait_until="networkidle", timeout=30_000)
            if response is None or response.status != 200:
                raise AssertionError("PWA did not load successfully")
            page.wait_for_timeout(1000)
            page.add_script_tag(path=str(axe_script))

            async_run = """async tags => {
              const r=await axe.run(document,{runOnly:{type:'tag',values:tags}});
              return {version:axe.version,violations:r.violations,incomplete:r.incomplete,passes:r.passes};
            }"""

            def scan(name: str) -> None:
                raw = page.evaluate(async_run, TAGS)
                scans[name] = summarize(raw)

            scan("dashboard_mobile_light")
            page.screenshot(path=str(OUT / "axe-v89-mobile-dashboard.png"))
            screenshots.append("axe-v89-mobile-dashboard.png")

            first_case = page.locator('[data-detail]:visible').first
            first_case.click()
            page.locator("#detail-dialog").wait_for(state="visible")
            scan("project_detail_mobile_light")
            page.screenshot(path=str(OUT / "axe-v89-mobile-detail.png"))
            screenshots.append("axe-v89-mobile-detail.png")
            page.keyboard.press("Escape")

            page.locator('[data-view="projects"]:visible').first.click()
            scan("projects_mobile_light")
            page.locator('[data-view="showcase"]:visible').first.click()
            scan("showcase_mobile_light")
            page.locator('[data-view="settings"]:visible').first.click()
            scan("settings_mobile_light")

            page.set_viewport_size({"width": 320, "height": 568})
            scan("settings_mobile_320_light")
            page.screenshot(path=str(OUT / "axe-v89-mobile-320-settings-light.png"))
            screenshots.append("axe-v89-mobile-320-settings-light.png")
            page.set_viewport_size({"width": 1440, "height": 1000})
            scan("settings_desktop_light")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#theme-toggle").click()
            scan("settings_mobile_dark")
            page.set_viewport_size({"width": 320, "height": 568})
            scan("settings_mobile_320_dark")
            page.set_viewport_size({"width": 1440, "height": 1000})
            scan("settings_desktop_dark")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator('[data-view="dashboard"]:visible').first.click()
            scan("dashboard_mobile_dark")

            page.set_viewport_size({"width": 1440, "height": 1000})
            scan("dashboard_desktop_dark")
            page.screenshot(path=str(OUT / "axe-v89-desktop-dashboard-dark.png"))
            screenshots.append("axe-v89-desktop-dashboard-dark.png")

            browser.close()

    total_violations = sum(scan["violation_count"] for scan in scans.values())
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "axe_core_version": AXE_VERSION,
        "tags": TAGS,
        "url": URL,
        "result": "PASS" if total_violations == 0 and not page_errors else "REVIEW_REQUIRED",
        "scan_count": len(scans),
        "total_violations_across_scans": total_violations,
        "scans": scans,
        "page_and_console_errors": page_errors,
        "screenshots": screenshots,
        "limits": [
            "Automated axe rules detect a subset of accessibility issues; they do not replace full WCAG conformance review.",
            "No physical screen reader, switch control, or human assistive-technology test was performed.",
        ],
    }
    (OUT / "axe-a11y-results-v89.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"axe-core {AXE_VERSION}: {result['result']}; {len(scans)} states, {total_violations} violations")
    if total_violations or page_errors:
        raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


