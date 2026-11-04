from __future__ import annotations

import asyncio
import json
import shutil
import threading
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
QA = SCRIPT_DIR
if SCRIPT_DIR.name.startswith("qa_"):
    PROJECT = SCRIPT_DIR.parents[1]
    PACKAGE = PROJECT / "Пакет_сдачи_портфолио_модули_4_5_на_проверку"
    APP_ROOT = PROJECT
    OLD_WEB = PACKAGE / "04_QA_доказательства" / "fixtures" / "sw-upgrade-v39-v40" / "v39-overlay"
else:
    PROJECT = SCRIPT_DIR.parent
    PACKAGE = PROJECT
    APP_ROOT = PROJECT / "02_Приложение"
    OLD_WEB = SCRIPT_DIR / "fixtures" / "sw-upgrade-v39-v40" / "v39-overlay"
NEW_WEB = APP_ROOT / "web"
FIXTURE_PARENT = Path(tempfile.mkdtemp(prefix="folio-sw-v39-v40-"))
FIXTURE = FIXTURE_PARENT / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


async def main() -> None:
    if FIXTURE.exists():
        raise FileExistsError(f"Refusing to overwrite isolated fixture: {FIXTURE}")
    shutil.copytree(NEW_WEB, FIXTURE)
    for relative in ("app.js", "core.js", "sw.js"):
        shutil.copy2(OLD_WEB / relative, FIXTURE / relative)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(FIXTURE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    result = {"before": {}, "after": {}, "offline": {}, "errors": []}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROME),
                args=["--no-first-run", "--no-default-browser-check"],
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900}, service_workers="allow"
            )
            page = await context.new_page()
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda message: result["errors"].append(message.text)
                    if message.type == "error" else None)
            response = await page.goto(url, wait_until="networkidle", timeout=15000)
            assert response and response.status == 200
            await page.wait_for_function(
                "async()=> (await caches.keys()).some(key=>key.includes('folio-shell-v39-strict-page-count'))",
                timeout=15000,
            )
            await page.wait_for_function("navigator.serviceWorker.controller !== null")
            result["before"] = {
                "cache_keys": await page.evaluate("caches.keys()"),
                "projects": await page.locator(".project-card").count(),
                "controller": await page.evaluate("navigator.serviceWorker.controller.scriptURL"),
            }

            await page.locator('[data-view="projects"]').first.click()
            await page.locator('[data-action="new-project"]').first.click()
            form = page.locator("#project-form")
            await form.locator('[name="title"]').fill("QA v40 URL privacy contract")
            await form.locator('[name="description"]').fill("Изолированная проверка формы после обновления PWA.")
            await form.locator('[name="created_at"]').fill("2026-10-29")
            await form.locator('[name="page_count"]').fill("2")
            await form.locator('[type="submit"]').click()
            await page.wait_for_function(
                "Array.from(document.querySelectorAll('.card-title')).some(item=>item.textContent.includes('QA v40 URL privacy contract'))",
                timeout=10000,
            )
            result["before"]["projects_after_form_save"] = await page.locator(".project-card").count()

            for source in NEW_WEB.rglob("*"):
                if source.is_file() and source.name != "sw.js":
                    target = FIXTURE / source.relative_to(NEW_WEB)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            shutil.copy2(NEW_WEB / "sw.js", FIXTURE / "sw.js")
            controller_change_observed = await page.evaluate("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              const change=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));
              await registration.update();
              return await Promise.race([change,new Promise(resolve=>setTimeout(()=>resolve(false),12000))]);
            }""")
            await page.wait_for_function(
                "async()=>{const keys=await caches.keys();return keys.length===1&&keys[0].includes('folio-shell-v40-url-credentials')}",
                timeout=20000,
                polling=250,
            )
            await page.wait_for_function("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              const keys=await caches.keys();
              return registration.active?.state==='activated'&&keys.length===1&&keys[0].includes('folio-shell-v40-url-credentials');
            }""", timeout=15000, polling=250)
            await page.wait_for_function(
                "navigator.serviceWorker.controller?.scriptURL.includes(location.host + '/sw.js')"
            )
            result["after"] = {
                "cache_keys": await page.evaluate("caches.keys()"),
                "projects": await page.locator(".project-card").count(),
                "new_case_visible": await page.locator(".project-card").filter(
                    has_text="QA v40 URL privacy contract"
                ).count(),
                "controller": await page.evaluate("navigator.serviceWorker.controller.scriptURL"),
            }
            result["after"]["registration_state"] = await page.evaluate("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              return {activeState:registration.active?.state,waitingState:registration.waiting?.state,
                installingState:registration.installing?.state,controller:navigator.serviceWorker.controller?.scriptURL};
            }""")
            result["after"]["controller_change_observed"] = controller_change_observed
            assert result["after"]["projects"] == 4, result["after"]
            assert result["after"]["new_case_visible"] == 1, result["after"]

            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded", timeout=10000)
            await page.locator(".project-card").first.wait_for(timeout=10000)
            await page.wait_for_function("""()=>[...document.querySelectorAll('.cover-image')]
              .filter(image=>image.getClientRects().length>0)
              .every(image=>image.complete&&image.naturalWidth>0)""", timeout=10000)
            await page.evaluate("""async()=>{
              await Promise.all([...document.images].map(image=>image.decode().catch(()=>{})));
              await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
            }""")
            result["offline"] = await page.evaluate("""()=>({
              projects:document.querySelectorAll('.project-card').length,
              retained:document.body.innerText.includes('QA v40 URL privacy contract'),
              documentWidth:document.documentElement.scrollWidth,
              viewportWidth:innerWidth
            })""")
            result["offline"]["cache_keys"] = await page.evaluate("caches.keys()")
            await page.screenshot(path=str(QA / "web-e2e-sw-upgrade-v39-v40-offline-1440x900.png"))
            assert result["offline"]["projects"] == 4, result["offline"]
            assert result["offline"]["retained"], result["offline"]
            assert result["offline"]["documentWidth"] == result["offline"]["viewportWidth"]
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.reload(wait_until="domcontentloaded", timeout=10000)
            await page.locator(".project-card").first.wait_for(timeout=10000)
            result["offline_mobile"] = await page.evaluate("""()=>(
              {projects:document.querySelectorAll('.project-card').length,
               retained:document.body.innerText.includes('QA v40 URL privacy contract'),
               documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth}
            )""")
            await page.screenshot(path=str(QA / "web-e2e-sw-upgrade-v39-v40-offline-390x844.png"))
            assert result["offline_mobile"]["projects"] == 4, result["offline_mobile"]
            assert result["offline_mobile"]["retained"], result["offline_mobile"]
            assert result["offline_mobile"]["documentWidth"] == result["offline_mobile"]["viewportWidth"]
            await context.set_offline(False)
            assert not result["errors"], result["errors"]
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        shutil.rmtree(FIXTURE_PARENT, ignore_errors=True)

    output = QA / "web-e2e-sw-upgrade-v39-v40-results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
