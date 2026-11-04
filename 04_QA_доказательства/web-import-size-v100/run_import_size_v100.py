from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"
MAX_BYTES = 64 * 1024 * 1024
FIXTURE = OUT / "oversized-valid-synthetic.json"


def make_fixture() -> None:
    prefix = b'{"projects":[],"padding":"'
    suffix = b'"}'
    remaining = MAX_BYTES + 1 - len(prefix) - len(suffix)
    with FIXTURE.open("wb") as stream:
        stream.write(prefix)
        block = b"x" * (1024 * 1024)
        while remaining >= len(block):
            stream.write(block)
            remaining -= len(block)
        if remaining:
            stream.write(b"x" * remaining)
        stream.write(suffix)


def main() -> None:
    make_fixture()
    browser_errors: list[str] = []
    result = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
            page = context.new_page()
            page.set_default_timeout(15_000)
            page.add_init_script("""
              window.__folioFileTextReads = 0;
              const originalFileText = File.prototype.text;
              File.prototype.text = function(...args) {
                window.__folioFileTextReads += 1;
                return originalFileText.apply(this, args);
              };
            """)
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
            response = page.goto(URL, wait_until="networkidle", timeout=30_000)
            if response is None or response.status != 200:
                raise AssertionError("Web app failed to load.")
            page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'")
            page.locator('[data-view="projects"]:visible').first.click()
            cards = page.locator(".project-card").count()
            if cards != 3:
                raise AssertionError(f"Expected 3 isolated demo projects, found {cards}.")
            if FIXTURE.stat().st_size != MAX_BYTES + 1:
                raise AssertionError("Oversized fixture does not exceed the configured size limit by exactly one byte.")
            page.locator("#import-file").set_input_files(str(FIXTURE))
            page.locator("#toast-region").get_by_text("Резервная копия больше 64 МиБ", exact=False).wait_for(state="visible")
            page.screenshot(path=str(OUT / "oversized-import-rejected-v100.png"), full_page=True)
            reads = page.evaluate("window.__folioFileTextReads")
            after_cards = page.locator(".project-card").count()
            if reads != 0:
                raise AssertionError(f"File.text() called {reads} time(s) before rejection.")
            if after_cards != cards:
                raise AssertionError(f"Project count changed from {cards} to {after_cards}.")
            if page.locator("#import-dialog[open]").count():
                raise AssertionError("Import preview opened for an oversized file.")
            if browser_errors:
                raise AssertionError(f"Browser errors: {browser_errors}")
            result = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "result": "PASS",
                "source": URL,
                "browser": "Isolated headless Chrome; service workers blocked; ephemeral IndexedDB context",
                "scenario": "Select a valid JSON file exactly one byte over the 64 MiB import limit through the application file input.",
                "file_size_bytes": FIXTURE.stat().st_size,
                "limit_bytes": MAX_BYTES,
                "file_text_reads_before_rejection": reads,
                "demo_projects_before": cards,
                "demo_projects_after": after_cards,
                "preview_opened": False,
                "browser_errors": browser_errors,
                "screenshot": "oversized-import-rejected-v100.png",
                "user_data_touched": False,
            }
            (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            browser.close()
    finally:
        FIXTURE.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
