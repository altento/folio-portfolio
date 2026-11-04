from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

QA = Path(__file__).resolve().parent
OLD_WEB = QA / "fixtures" / "sw-upgrade-v49-v50" / "v49-overlay"
NEW_WEB = QA.parent / "02_Приложение" / "web"
TEMP = Path(tempfile.mkdtemp(prefix="folio-v49-v50-case-guide-"))
SITE = TEMP / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class Handler(SimpleHTTPRequestHandler):
    requests: list[str] = []

    def do_GET(self):
        self.requests.append(self.path)
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *_args):
        pass


async def main():
    shutil.copytree(NEW_WEB, SITE)
    for src in OLD_WEB.rglob("*"):
        if src.is_file():
            dst = SITE / src.relative_to(OLD_WEB)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result = {"errors": [], "upgrade": {}, "guide": {}, "save": {}, "offline": {}}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path=str(CHROME),
                args=["--no-first-run", "--no-default-browser-check"],
            )
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="allow")
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda msg: result["errors"].append(msg.text) if msg.type == "error" else None)
            response = await page.goto(f"http://127.0.0.1:{server.server_port}/#dashboard", wait_until="networkidle", timeout=20000)
            assert response and response.status == 200
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v49-manual-update-notice')", timeout=15000)
            await page.wait_for_function("navigator.serviceWorker.controller!==null", timeout=15000)
            # The old app captures controller availability when app.js evaluates.
            # Reload once under the now-active v49 worker to model an installed PWA
            # that was already controlled before an update became available.
            await page.reload(wait_until="networkidle", timeout=20000)
            await page.wait_for_function("navigator.serviceWorker.controller!==null", timeout=15000)
            old_time_origin = await page.evaluate("performance.timeOrigin")

            for src in NEW_WEB.rglob("*"):
                if src.is_file():
                    dst = SITE / src.relative_to(NEW_WEB)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            (SITE / "sw.js").touch()
            Handler.requests.clear()
            changed = await page.evaluate("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              const event=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));
              await registration.update();
              return Promise.race([event,new Promise(resolve=>setTimeout(()=>resolve(false),15000))]);
            }""")
            await page.locator("#update-notice").wait_for(state="visible", timeout=10000)
            result["upgrade"] = {
                "controllerChanged": changed,
                "pageStayedOpen": await page.evaluate("performance.timeOrigin") == old_time_origin,
                "noticeVisible": await page.locator("#update-notice").is_visible(),
                "requestedWorker": any("sw.js" in request for request in Handler.requests),
            }
            assert all(result["upgrade"].values())
            await page.locator("#update-reload").click()
            await page.wait_for_load_state("domcontentloaded", timeout=12000)
            await page.locator("#update-notice").wait_for(state="hidden", timeout=10000)
            await page.wait_for_function("async()=>{const keys=await caches.keys();return keys.length===1&&keys[0]==='folio-shell-v50-case-story-guide'}", timeout=15000)

            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            form = page.locator("#project-form")
            progress = page.get_by_role("progressbar", name="История кейса")
            await progress.wait_for(state="visible")
            result["guide"]["initial"] = await progress.get_attribute("aria-valuenow")
            # Prove that the story prompts are guidance only: the ordinary required
            # fields suffice to save a project while all six guide blocks stay empty.
            await form.locator('[name="title"]').fill("Кейс без дополнительных подсказок")
            await form.locator('[name="description"]').fill("Подтверждение, что структура истории не обязательна.")
            await form.locator('[name="created_at"]').fill("2026-10-30")
            await form.locator('[type="submit"]').click()
            await page.get_by_text("Кейс без дополнительных подсказок", exact=True).first.wait_for(timeout=10000)
            result["guide"]["optionalNotBlocking"] = (
                result["guide"]["initial"] == "0"
                and await page.get_by_text("Кейс без дополнительных подсказок", exact=True).count() == 1
            )
            assert result["guide"]["optionalNotBlocking"]

            await page.locator('[data-action="new-project"]:visible').first.click()
            form = page.locator("#project-form")
            progress = page.get_by_role("progressbar", name="История кейса")
            await progress.wait_for(state="visible")
            await form.locator('[name="title"]').fill("QA кейс со структурой истории")
            await form.locator('[name="description"]').fill("Проверка ненавязчивых рекомендаций в редакторе кейса.")
            await form.locator('[name="created_at"]').fill("2026-10-30")
            for value, expected in [
                ("Задача учебной команды", "1"),
                ("Исследование и интерфейс", "2"),
                ("Сделать путь короче", "3"),
                ("Интервью, прототип, проверка", "4"),
                ("Пользователь оформляет запись за один шаг", "5"),
            ]:
                name = {"1": "context", "2": "role", "3": "solution", "4": "process", "5": "outcome"}[expected]
                await form.locator(f'[name="{name}"]').fill(value)
                await page.wait_for_function("(expected)=>document.querySelector('#case-guide-progress')?.getAttribute('aria-valuenow')===expected", arg=expected)
            cover = OLD_WEB / "assets" / "covers" / "portfolio-studio.webp"
            await page.locator("#cover-file").set_input_files(str(cover))
            await page.wait_for_function("document.querySelector('#case-guide-progress')?.getAttribute('aria-valuenow')==='6'", timeout=10000)
            await page.locator(".case-guide-details summary").click()
            guide_rows = await page.locator(".case-guide-list li").evaluate_all("els=>els.map(el=>({key:el.dataset.caseGuide,complete:el.dataset.complete}))")
            assert len(guide_rows) == 6 and all(row["complete"] == "true" for row in guide_rows), guide_rows
            result["guide"]["milestones"] = [
                await progress.get_attribute("aria-valuenow") if value == "cover" else expected
                for value, expected in [("start", "0"), ("context", "1"), ("role", "2"), ("solution", "3"), ("process", "4"), ("outcome", "5"), ("cover", "6")]
            ]
            result["guide"]["finalRows"] = guide_rows
            result["guide"]["summaryTargetHeight"] = await page.locator(".case-guide-details summary").evaluate("el=>Math.round(el.getBoundingClientRect().height)")
            assert result["guide"]["initial"] == "0"
            assert result["guide"]["summaryTargetHeight"] >= 44

            await page.screenshot(path=str(QA / "web-case-guide-v50-desktop-1440x900.png"))
            result["guide"]["desktopWidth"] = await page.evaluate("document.documentElement.scrollWidth")
            await page.set_viewport_size({"width": 390, "height": 844})
            result["guide"]["mobile390Width"] = await page.evaluate("document.documentElement.scrollWidth")
            await page.screenshot(path=str(QA / "web-case-guide-v50-mobile-390x844.png"))
            await page.set_viewport_size({"width": 320, "height": 568})
            result["guide"]["mobile320Width"] = await page.evaluate("document.documentElement.scrollWidth")
            await page.screenshot(path=str(QA / "web-case-guide-v50-mobile-320x568.png"))
            assert result["guide"]["desktopWidth"] == 1440
            assert result["guide"]["mobile390Width"] == 390 and result["guide"]["mobile320Width"] == 320

            await form.locator('[type="submit"]').click()
            await page.get_by_text("QA кейс со структурой истории", exact=True).first.wait_for(timeout=10000)
            result["save"]["savedCardVisible"] = True
            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded", timeout=12000)
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.get_by_text("QA кейс со структурой истории", exact=True).first.wait_for(timeout=10000)
            result["offline"] = {
                "recordRetained": await page.get_by_text("QA кейс со структурой истории", exact=True).count() == 1,
                "cacheKeys": await page.evaluate("caches.keys()"),
                "documentWidth": await page.evaluate("document.documentElement.scrollWidth"),
                "viewportWidth": await page.evaluate("innerWidth"),
            }
            assert result["offline"]["recordRetained"]
            assert result["offline"]["cacheKeys"] == ["folio-shell-v50-case-story-guide"]
            assert result["offline"]["documentWidth"] == result["offline"]["viewportWidth"]
            assert not result["errors"], result["errors"]
            await context.set_offline(False)
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        shutil.rmtree(TEMP, ignore_errors=True)

    (QA / "web-case-guide-v50-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
