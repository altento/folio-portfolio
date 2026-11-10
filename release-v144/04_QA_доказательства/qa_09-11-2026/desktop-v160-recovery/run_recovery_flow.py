from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
PROFILE = Path(os.environ.get(
    "FOLIO_RECOVERY_PROFILE",
    r"C:\Users\Windows-10\AppData\Local\Temp\folio-v160-recovery-qa",
))
URL = os.environ.get(
    "FOLIO_RECOVERY_URL",
    "http://127.0.0.1:41800/?folio-desktop=1#projects",
)
CHROME = Path(os.environ.get(
    "FOLIO_CHROME_EXECUTABLE",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
))


def make_synthetic_snapshot(profile: Path) -> tuple[bytes, bytes, str]:
    sys.path.insert(0, str(ROOT))
    from desktop_webview import DesktopFileApi

    snapshot_path = profile / "folio-recovery-v1.json"
    original = snapshot_path.read_bytes()
    envelope = json.loads(original.decode("utf-8"))
    portfolio = envelope["portfolio"]
    projects = portfolio["projects"]
    marker = json.loads(json.dumps(projects[0], ensure_ascii=False))
    marker.update({
        "id": 9001,
        "project_id": 9001,
        "sort_order": len(projects) + 1,
        "title": "QA: восстановленный проект",
        "description": "Синтетическая запись для проверки локального восстановления.",
        "created_at": "2026-11-10",
        "featured": False,
        "role": "Изолированный тест восстановления",
        "outcome": "Запись появилась после загрузки локальной копии.",
    })
    portfolio["projects"] = [*projects, marker]
    portfolio["next_id"] = 9002
    portfolio["demo"] = False
    DesktopFileApi(profile).save_recovery_snapshot(json.dumps(portfolio, ensure_ascii=False))
    candidate = snapshot_path.read_bytes()
    return original, candidate, hashlib.sha256(candidate).hexdigest()


async def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not CHROME.is_file():
        raise FileNotFoundError(CHROME)
    original: bytes | None = None
    errors: list[str] = []
    result: dict[str, object] = {
        "scope": "Fresh isolated Chrome context loading the exact Windows v160 loopback recovery endpoint with a minimal pywebview bridge stub; no native WebView2 storage or user browser profile was used.",
        "url": URL,
        "profile": str(PROFILE),
        "syntheticOnly": True,
    }
    try:
        original, candidate, candidate_sha256 = make_synthetic_snapshot(PROFILE)
        result["candidateSnapshotSha256"] = candidate_sha256
        result["candidateProjectCount"] = 4
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROME),
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=1,
                locale="ru-RU",
                service_workers="block",
            )
            await context.add_init_script("""window.pywebview = {api: {
              save_recovery_snapshot: async () => ({saved_at: new Date().toISOString()})
            }};""")
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
            page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
            response = await page.goto(URL, wait_until="networkidle", timeout=20000)
            if response is None or response.status != 200:
                raise AssertionError(f"Recovery page returned {response.status if response else 'no response'}")
            await page.wait_for_function(
                "document.querySelector('#main-content')?.getAttribute('aria-busy') === 'false'",
                timeout=20000,
            )
            await page.wait_for_function(
                "document.querySelectorAll('.project-card').length === 4",
                timeout=15000,
            )
            await page.locator('[data-view="projects"]:visible').first.click()
            await page.locator("#main-content h1").first.wait_for(state="visible")
            await page.wait_for_function(
                "document.querySelectorAll('.project-card').length === 4",
                timeout=10000,
            )
            marker = page.get_by_text("QA: восстановленный проект", exact=True).first
            await marker.wait_for(state="visible", timeout=5000)
            screenshot = OUTPUT / "recovered-projects-v160-1440x900.png"
            await page.screenshot(path=str(screenshot), full_page=True)
            titles = await page.locator(".project-card").evaluate_all(
                "cards => cards.map(card => card.innerText.trim()).filter(Boolean)"
            )
            result.update({
                "pageStatus": response.status,
                "recoveredProjectCards": await page.locator(".project-card").count(),
                "syntheticMarkerVisible": await marker.is_visible(),
                "visibleTitles": titles,
                "pageErrors": errors,
                "screenshot": screenshot.name,
                "screenshotSha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                "passed": any("QA: восстановленный проект" in title for title in titles) and not errors,
            })
            await context.close()
            await browser.close()
    finally:
        if original is not None:
            snapshot_path = PROFILE / "folio-recovery-v1.json"
            temporary = snapshot_path.with_suffix(".json.restore-tmp")
            temporary.write_bytes(original)
            temporary.replace(snapshot_path)
            result["originalSnapshotRestored"] = hashlib.sha256(snapshot_path.read_bytes()).digest() == hashlib.sha256(original).digest()

    result_path = OUTPUT / "result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("passed") is not True or result.get("originalSnapshotRestored") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
