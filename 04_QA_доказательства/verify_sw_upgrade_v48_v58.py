from __future__ import annotations

import asyncio
import json
import re
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright

QA = Path(__file__).resolve().parent
PROJECT = QA.parents[1]
OLD_WEB = QA / "fixtures" / "sw-upgrade-v48-v49" / "v48-overlay"
PACKAGED_WEB = QA.parent / "02_Приложение" / "web"
NEW_WEB = PACKAGED_WEB if PACKAGED_WEB.is_dir() else PROJECT / "web"
TEMP = Path(tempfile.mkdtemp(prefix="folio-v48-v58-upgrade-"))
SITE = TEMP / "site"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CURRENT_CACHE = re.search(r"const CACHE=['\"]([^'\"]+)['\"]", (NEW_WEB / "sw.js").read_text(encoding="utf-8")).group(1)
SIMULATED_CACHE = CURRENT_CACHE + "-simulated-next"


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
    result = {"from": "v48", "to": CURRENT_CACHE, "errors": [], "before": {}, "legacyV48ToCurrent": {}, "update": {}, "afterReload": {}, "offline": {}}
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
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v48-compact-sort-labels')", timeout=15000)
            await page.wait_for_function("navigator.serviceWorker.controller!==null", timeout=15000)
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            form = page.locator("#project-form")
            await form.locator('[name="title"]').fill("QA v48 → v58: сохранённая запись")
            await form.locator('[name="description"]').fill("Запись в изолированном профиле для проверки обновления, сохранения данных и офлайн-перехода.")
            await form.locator('[name="created_at"]').fill("2026-10-30")
            await form.locator('[type="submit"]').click()
            await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).first.wait_for(timeout=10000)
            result["before"] = {"httpStatus": response.status, "cacheKeys": await page.evaluate("caches.keys()"), "recordSaved": True}

            for src in NEW_WEB.rglob("*"):
                if src.is_file():
                    dst = SITE / src.relative_to(NEW_WEB)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            (SITE / "sw.js").touch()
            Handler.requests.clear()
            controller_changed = await page.evaluate("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              const changed=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));
              await registration.update();
              return Promise.race([changed,new Promise(resolve=>setTimeout(()=>resolve(false),15000))]);
            }""")
            await page.wait_for_function(f"async()=>{{const keys=await caches.keys();return keys.length===1&&keys[0]==='{CURRENT_CACHE}'}}", timeout=20000)
            result["legacyV48ToCurrent"] = {
                "controllerChange": controller_changed,
                "legacyNoticeUnavailableUntilReload": await page.locator("#update-notice").count() == 0,
                "recordStillVisible": await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).count() == 1,
            }
            assert result["legacyV48ToCurrent"]["controllerChange"]
            assert result["legacyV48ToCurrent"]["recordStillVisible"]
            await page.reload(wait_until="domcontentloaded", timeout=12000)
            await page.locator("#update-notice").wait_for(state="hidden", timeout=10000)
            await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).first.wait_for(timeout=10000)
            old_time_origin = await page.evaluate("performance.timeOrigin")

            # The current runtime has the update listener. Simulate a subsequent
            # cache version to verify that a live page receives the banner.
            next_worker = (SITE / "sw.js").read_text(encoding="utf-8")
            assert CURRENT_CACHE in next_worker
            (SITE / "sw.js").write_text(next_worker.replace(CURRENT_CACHE, SIMULATED_CACHE), encoding="utf-8")
            (SITE / "sw.js").touch()
            Handler.requests.clear()
            controller_changed = await page.evaluate("""async()=>{
              const registration=await navigator.serviceWorker.getRegistration();
              const changed=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));
              await registration.update();
              return Promise.race([changed,new Promise(resolve=>setTimeout(()=>resolve(false),15000))]);
            }""")
            await page.wait_for_function(f"async()=> (await caches.keys()).includes('{SIMULATED_CACHE}')", timeout=20000)
            await page.locator("#update-notice").wait_for(state="visible", timeout=10000)
            await page.wait_for_function(f"async()=>{{const keys=await caches.keys();return keys.length===1&&keys[0]==='{SIMULATED_CACHE}'}}", timeout=10000)
            await page.wait_for_timeout(250)
            result["update"] = {
                "controllerChange": controller_changed,
                "noticeVisible": await page.locator("#update-notice").is_visible(),
                "noticeText": (await page.locator("#update-notice").inner_text()).strip(),
                "pageStayedOpen": await page.evaluate("performance.timeOrigin") == old_time_origin,
                "recordStillVisible": await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).count() == 1,
                "requestedWorker": any("sw.js" in path for path in Handler.requests),
            }
            assert result["update"]["controllerChange"] and result["update"]["noticeVisible"]
            assert result["update"]["pageStayedOpen"] and result["update"]["recordStillVisible"]
            assert result["update"]["requestedWorker"]
            await page.locator("#theme-toggle").click()
            result["update"]["darkTheme"] = await page.locator("#update-notice").evaluate("""el=>{
              const text=getComputedStyle(el.querySelector('p')).color,background=getComputedStyle(el).backgroundColor;
              const rgb=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number);
              const luminance=c=>c.reduce((v,x,i)=>{x/=255;x=x<=.04045?x/12.92:((x+.055)/1.055)**2.4;return v+x*[.2126,.7152,.0722][i]},0);
              const a=luminance(rgb(text)),b=luminance(rgb(background));
              return {theme:document.documentElement.dataset.theme,text,background,contrast:+((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toFixed(2)};
            }""")
            assert result["update"]["darkTheme"]["theme"] == "dark" and result["update"]["darkTheme"]["contrast"] >= 4.5
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-dark-desktop-1440x900.png"))
            await page.locator("#theme-toggle").click()
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-desktop-1440x900.png"))

            await page.set_viewport_size({"width": 390, "height": 844})
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-mobile-390x844.png"))
            result["update"]["mobile"] = await page.evaluate("""()=>({
              visible:!!document.querySelector('#update-notice')&&!document.querySelector('#update-notice').hidden,
              scrollWidth:document.documentElement.scrollWidth,
              viewportWidth:innerWidth,
              reloadButtonWidth:Math.round(document.querySelector('#update-reload').getBoundingClientRect().width)
            })""")
            assert result["update"]["mobile"]["visible"]
            assert result["update"]["mobile"]["scrollWidth"] == result["update"]["mobile"]["viewportWidth"]
            await page.set_viewport_size({"width": 320, "height": 568})
            result["update"]["mobile320"] = await page.evaluate("""()=>({
              visible:!!document.querySelector('#update-notice')&&!document.querySelector('#update-notice').hidden,
              scrollWidth:document.documentElement.scrollWidth,
              viewportWidth:innerWidth
            })""")
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-mobile-320x568.png"))
            assert result["update"]["mobile320"]["visible"]
            assert result["update"]["mobile320"]["scrollWidth"] == 320
            await page.set_viewport_size({"width": 390, "height": 844})

            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            draft = page.locator("#project-form")
            await draft.locator('[name="title"]').fill("QA черновик при обновлении")
            await draft.locator('[name="description"]').fill("Черновик должен пережить обновление после явного нажатия.")
            await draft.locator('[name="created_at"]').fill("2026-10-30")
            await page.get_by_text("Черновик сохранён на этом устройстве.", exact=True).wait_for(timeout=10000)
            await page.keyboard.press("Escape")
            await page.locator("#project-dialog").wait_for(state="hidden", timeout=5000)

            await page.locator("#update-reload").click()
            await page.wait_for_load_state("domcontentloaded", timeout=12000)
            await page.locator("#update-notice").wait_for(state="hidden", timeout=10000)
            await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).first.wait_for(timeout=10000)
            await page.locator('nav [data-view="projects"]:visible').click()
            page.once("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            await page.locator('[data-action="new-project"]:visible').first.click()
            await page.get_by_text("Черновик восстановлен", exact=False).wait_for(timeout=10000)
            restored_draft_title = await page.locator('#project-form [name="title"]').input_value()
            assert restored_draft_title == "QA черновик при обновлении", ascii(restored_draft_title)
            await page.keyboard.press("Escape")
            result["afterReload"] = {
                "noticeHidden": await page.locator("#update-notice").is_hidden(),
                "recordRetained": await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).count() == 1,
                "draftRetained": restored_draft_title == "QA черновик при обновлении",
                "cacheKeys": await page.evaluate("caches.keys()"),
            }
            assert result["afterReload"]["noticeHidden"] and result["afterReload"]["recordRetained"] and result["afterReload"]["draftRetained"]
            assert result["afterReload"]["cacheKeys"] == [SIMULATED_CACHE]

            await page.set_viewport_size({"width": 1440, "height": 900})
            await context.set_offline(True)
            await page.reload(wait_until="domcontentloaded", timeout=12000)
            await page.get_by_text("QA v48 → v58: сохранённая запись", exact=True).first.wait_for(timeout=10000)
            result["offline"] = await page.evaluate("""()=>({
              title:document.title,
              recordVisible:document.body.innerText.includes('QA v48 → v58: сохранённая запись'),
              cacheKeys:null,
              viewportWidth:innerWidth,
              documentWidth:document.documentElement.scrollWidth
            })""")
            result["offline"]["cacheKeys"] = await page.evaluate("caches.keys()")
            assert result["offline"]["recordVisible"]
            assert result["offline"]["cacheKeys"] == [SIMULATED_CACHE]
            assert result["offline"]["documentWidth"] == result["offline"]["viewportWidth"]
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-offline-desktop-1440x900.png"))
            await page.set_viewport_size({"width": 390, "height": 844})
            result["offline"]["mobileDocumentWidth"] = await page.evaluate("document.documentElement.scrollWidth")
            result["offline"]["mobileViewportWidth"] = await page.evaluate("innerWidth")
            await page.screenshot(path=str(QA / "web-update-notice-v48-v58-offline-mobile-390x844.png"))
            assert result["offline"]["mobileDocumentWidth"] == result["offline"]["mobileViewportWidth"]
            assert not result["errors"], result["errors"]
            await context.set_offline(False)
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        shutil.rmtree(TEMP, ignore_errors=True)

    output = QA / "web-update-notice-v48-v58-results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
