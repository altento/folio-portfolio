import asyncio
import json
import threading
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.name.startswith("qa_"):
    ROOT = SCRIPT_DIR.parents[1]
    WEB = ROOT / "web"
    QA = SCRIPT_DIR
else:
    ROOT = SCRIPT_DIR.parent
    WEB = ROOT / "02_Приложение" / "web"
    QA = SCRIPT_DIR
ROUTES = ["dashboard", "projects", "showcase", "settings"]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


async def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    result = {"date":"2026-10-30", "version":"folio-shell-v58-illustrated-dashboard-hero", "errors":[], "screens":[], "views":[], "external_requests":[]}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", args=["--no-first-run", "--no-default-browser-check"])
            context = await browser.new_context(viewport={"width":1440,"height":900}, service_workers="allow")
            await context.add_init_script("""(()=>{
              const original=EventTarget.prototype.addEventListener;
              window.__folioDialogCloseFocusHandlerCounts={};
              EventTarget.prototype.addEventListener=function(type,listener,options){
                if(type==='close'&&this instanceof HTMLDialogElement&&String(listener).includes('dialogOpeners.get(dialog)')){
                  const id=this.id||'(unnamed)';
                  window.__folioDialogCloseFocusHandlerCounts[id]=(window.__folioDialogCloseFocusHandlerCounts[id]||0)+1;
                }
                return original.call(this,type,listener,options);
              };
            })();""")
            page = await context.new_page()
            page.on("request", lambda request: result["external_requests"].append({"host":urlsplit(request.url).hostname,"type":request.resource_type,"frame":request.frame.url if request.frame else None}) if not request.url.startswith(url) and not request.url.startswith("data:") else None)
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.on("console", lambda message: result["errors"].append(message.text) if message.type=="error" else None)
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await page.wait_for_function("Object.keys(window.__folioDialogCloseFocusHandlerCounts).length > 0")
            result["script_hosts"] = await page.locator("script[src]").evaluate_all("items=>items.map(s=>new URL(s.src).hostname)")
            result["dialog_focus_handlers"] = await page.evaluate("window.__folioDialogCloseFocusHandlerCounts")
            assert result["dialog_focus_handlers"] and all(count == 1 for count in result["dialog_focus_handlers"].values()), result["dialog_focus_handlers"]
            for width,height in [(1440,900),(390,844),(320,568)]:
                await page.set_viewport_size({"width":width,"height":height})
                for route in ROUTES:
                    selector = f".mobile-nav [data-view='{route}']" if width < 821 else f".sidebar .nav-item[data-view='{route}']"
                    await page.locator(selector).click()
                    await page.wait_for_timeout(80)
                    metrics = await page.evaluate("""()=>{
                      const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0};
                      const controls=[...document.querySelectorAll('button,a[href],input:not([type=file]),select,textarea,[role=button]')].filter(visible);
                      const name=e=>{const by=e.getAttribute('aria-label');if(by)return by;const labelled=e.getAttribute('aria-labelledby');if(labelled)return labelled.split(/\\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ').trim();const labels=e.labels?[...e.labels].map(x=>x.innerText.trim()).filter(Boolean):[];if(labels.length)return labels.join(' ');return (e.innerText||e.getAttribute('alt')||e.getAttribute('title')||e.getAttribute('placeholder')||'').trim()};
                      const unnamed=controls.filter(e=>!name(e)).map(e=>({tag:e.tagName,type:e.type||'',role:e.getAttribute('role'),html:e.outerHTML.slice(0,160)}));
                      const unlabeled=[...document.querySelectorAll('input:not([type=hidden]):not([type=file]),select,textarea')].filter(visible).filter(e=>!(e.labels?.length||e.getAttribute('aria-label')||e.getAttribute('aria-labelledby'))).map(e=>({tag:e.tagName,type:e.type||'',name:e.name||'',id:e.id}));
                      const targets=controls.map(e=>{let t=e;if((e.type==='checkbox'||e.type==='radio')&&e.labels?.[0])t=e.labels[0];const r=t.getBoundingClientRect();return {name:name(e).slice(0,70),w:Math.round(r.width),h:Math.round(r.height),tag:e.tagName,inline:e.tagName==='A'&&!e.classList.contains('button')}});
                      const imgs=[...document.images].filter(visible).map(i=>({alt:i.getAttribute('alt'),loaded:i.complete&&i.naturalWidth>0,src:i.getAttribute('src')}));
                      return {controlCount:targets.length,smallestTarget:targets.length?Math.min(...targets.flatMap(t=>[t.w,t.h])):0,viewport:{width:innerWidth,height:innerHeight},document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},h1:[...document.querySelectorAll('h1')].filter(visible).length,landmarks:{main:document.querySelectorAll('main').length,nav:document.querySelectorAll('nav').length},unnamed,unlabeled,smallTargets:targets.filter(t=>(t.w<24||t.h<24)&&!t.inline),targetsUnder44:targets.filter(t=>(t.w<44||t.h<44)&&!t.inline),imagesMissingAlt:imgs.filter(i=>i.alt===null),imagesNotLoaded:imgs.filter(i=>!i.loaded),imageCount:imgs.length};
                    }""")
                    entry={"width":width,"height":height,"route":route,**metrics}
                    assert metrics["document"]["width"]==width,entry
                    assert not metrics["unnamed"] and not metrics["unlabeled"],entry
                    assert not metrics["smallTargets"],entry
                    if width < 821:
                        assert not metrics["targetsUnder44"],entry
                    assert not metrics["imagesMissingAlt"] and not metrics["imagesNotLoaded"],entry
                    assert metrics["h1"]==1 and metrics["landmarks"]["main"]>=1,entry
                    result["views"].append(entry)
                    shot=f"web-a11y-v58-{route}-{width}x{height}.png"
                    await page.screenshot(path=str(QA/shot))
                    result["screens"].append(shot)
                # Detail and editor dialogs on both representative widths.
                selector=f".mobile-nav [data-view='projects']" if width<821 else ".sidebar .nav-item[data-view='projects']"
                await page.locator(selector).click()
                await page.locator("[data-detail]").first.click()
                await page.locator("#detail-dialog[open]").wait_for()
                detail=await page.evaluate("""()=>({dialogOpen:document.querySelector('#detail-dialog').open,ariaLabelledby:document.querySelector('#detail-dialog').getAttribute('aria-labelledby'),titleId:!!document.querySelector('#detail-title'),closeName:document.querySelector('#detail-dialog [data-close-dialog]')?.getAttribute('aria-label'),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth})""")
                assert detail["dialogOpen"] and detail["ariaLabelledby"] and detail["titleId"] and detail["closeName"] and detail["documentWidth"]==width,detail
                result.setdefault("details",[]).append({"width":width,**detail})
                shot=f"web-a11y-v58-detail-{width}x{height}.png"
                await page.screenshot(path=str(QA/shot));result["screens"].append(shot)
                await page.keyboard.press("Escape")
                await page.locator("#detail-dialog").wait_for(state="hidden")
                await page.locator("[data-action='new-project']:visible").first.click()
                await page.locator("#project-dialog[open]").wait_for()
                form=await page.evaluate("""()=>({dialogOpen:document.querySelector('#project-dialog').open,documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,activeName:document.activeElement?.name||document.activeElement?.id||document.activeElement?.tagName,actions:[...document.querySelectorAll('#project-dialog .dialog-actions button')].map(b=>{let r=b.getBoundingClientRect();return {label:b.innerText.trim(),w:Math.round(r.width),h:Math.round(r.height),visible:r.top>=0&&r.bottom<=innerHeight}}),unlabeled:[...document.querySelectorAll('#project-dialog input:not([type=hidden]),#project-dialog select,#project-dialog textarea')].filter(e=>e.offsetWidth&&!(e.labels?.length||e.getAttribute('aria-label')||e.getAttribute('aria-labelledby'))).map(e=>e.name||e.id)})""")
                assert form["dialogOpen"] and form["documentWidth"]==width and not form["unlabeled"],form
                form["headingVisibleAtOpen"]=await page.evaluate("()=>{const r=document.querySelector('#project-dialog .dialog-head').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}")
                assert form["headingVisibleAtOpen"],form
                if width==320:
                    shot=f"web-a11y-v58-form-start-{width}x{height}.png"
                    await page.screenshot(path=str(QA/shot));result["screens"].append(shot)
                await page.locator("#project-dialog .dialog-actions button").last.scroll_into_view_if_needed()
                form["actionsAfterScroll"]=await page.evaluate("""()=>[...document.querySelectorAll('#project-dialog .dialog-actions button')].map(b=>{let r=b.getBoundingClientRect();return {label:b.innerText.trim(),w:Math.round(r.width),h:Math.round(r.height),visible:r.top>=0&&r.bottom<=innerHeight}})""")
                assert all(action["visible"] for action in form["actionsAfterScroll"]),form
                result.setdefault("forms",[]).append({"width":width,**form})
                shot=f"web-a11y-v58-form-{width}x{height}.png"
                await page.screenshot(path=str(QA/shot));result["screens"].append(shot)
                await page.keyboard.press("Escape")
                await page.locator("#project-dialog").wait_for(state="hidden")
            await page.emulate_media(reduced_motion="reduce")
            result["reduced_motion"] = await page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
            assert result["reduced_motion"] is True
            await page.emulate_media(reduced_motion="no-preference")
            await page.locator("#theme-toggle").click()
            result["dark_theme"] = await page.evaluate("document.documentElement.dataset.theme")
            await page.locator("#theme-toggle").click()
            result["light_theme_restored"] = await page.evaluate("document.documentElement.dataset.theme")
            assert result["dark_theme"]=="dark" and result["light_theme_restored"]=="light",result
            await context.close();await browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    (QA/"web-accessibility-audit-v58-2026-10-30.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"views":len(result["views"]),"details":result.get("details"),"forms":result.get("forms"),"errors":result["errors"],"external_requests":result["external_requests"],"script_hosts":result.get("script_hosts"),"reduced_motion":result.get("reduced_motion"),"theme":(result.get("dark_theme"),result.get("light_theme_restored")),"dialog_focus_handlers":result.get("dialog_focus_handlers"),"screens":result["screens"]},ensure_ascii=False,indent=2))

asyncio.run(main())





