from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8766/"


def main() -> None:
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block", accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(10_000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        response = page.goto(URL, wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise AssertionError("Current v99 web build did not load successfully.")
        page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'")
        page.locator('[data-action="new-project"]:visible').first.click()
        page.locator('#project-form [name="title"]').fill("=1+1")
        page.locator('#project-form [name="description"]').fill("+SUM(1,2)")
        page.locator('#project-form [name="role"]').fill("@SUM(1,2)")
        page.locator('#project-form [name="solution"]').fill("＝1+1")
        page.get_by_role("button", name="Сохранить проект").click()
        page.get_by_role("button", name="=1+1").wait_for(state="visible")
        page.locator('[data-view="settings"]:visible').first.click()
        page.wait_for_selector("#storage-reliability[data-storage-status]:visible")
        page.screenshot(path=str(OUT / "csv-export-v99-settings.png"), full_page=True)
        with page.expect_download() as pending_download:
            page.locator('[data-action="export-csv"]').click()
        download = pending_download.value
        csv_path = OUT / "formula-neutralized-synthetic.csv"
        await_path = str(csv_path)
        download.save_as(await_path)
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        row = next(item for item in rows if item["title"] == "'=1+1")
        expected = {
            "title": "'=1+1",
            "description": "'+SUM(1,2)",
            "role": "'@SUM(1,2)",
            "solution": "'＝1+1",
        }
        if any(row[key] != value for key, value in expected.items()):
            raise AssertionError(f"CSV formula neutralization mismatch: {row}")
        ordinary = next(item for item in rows if item["title"] == "Портфолио веб-разработчика")
        if not ordinary["title"] or ordinary["description"].startswith("'"):
            raise AssertionError("Ordinary demo values were changed by formula neutralization.")
        if errors:
            raise AssertionError(f"Browser errors: {errors}")
        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "result": "PASS",
            "source": URL,
            "browser_context": "Fresh isolated Chromium context; service workers blocked; only ephemeral IndexedDB was written.",
            "scenario": "Create a synthetic case with ASCII and full-width spreadsheet formula starters, export CSV through Settings, parse the downloaded file.",
            "expected_neutralized_cells": expected,
            "ordinary_values_preserved": True,
            "browser_errors": errors,
            "synthetic_export": csv_path.name,
            "screenshot": "csv-export-v99-settings.png",
            "user_data_touched": False,
        }
        (OUT / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        browser.close()
        print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

