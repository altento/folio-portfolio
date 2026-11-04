from __future__ import annotations
import asyncio,json,shutil,threading,tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
QA=Path(__file__).resolve().parent
PROJECT=QA.parents[1]
OLD_WEB=QA/'fixtures'/'sw-upgrade-v45-v46'/'v45-overlay'
CURRENT_WEB=PROJECT/'web'
V46_OVERLAY=QA/'fixtures'/'sw-upgrade-v46-v47'/'v46-overlay'
TEMP=Path(tempfile.mkdtemp(prefix='folio-v45-v46-'))
NEW_WEB=TEMP/'web-v46'
SITE=TEMP/'site'
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
    requests=[]
    def do_GET(self):
        self.requests.append(self.path)
        super().do_GET()
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def log_message(self,*args):
        pass
async def main():
    if SITE.exists(): raise FileExistsError(SITE)
    shutil.copytree(CURRENT_WEB,NEW_WEB)
    for src in V46_OVERLAY.rglob('*'):
        if src.is_file():
            dst=NEW_WEB/src.relative_to(V46_OVERLAY);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    shutil.copytree(NEW_WEB,SITE)
    for src in OLD_WEB.rglob('*'):
        if src.is_file():
            dst=SITE/src.relative_to(OLD_WEB);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    result={'errors':[],'before':{},'after':{},'offline':{}}
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check'])
            context=await browser.new_context(viewport={'width':1440,'height':900},service_workers='allow')
            page=await context.new_page()
            page.on('pageerror',lambda error:result['errors'].append(str(error)))
            page.on('console',lambda message:result['errors'].append(message.text) if message.type=='error' else None)
            response=await page.goto(f'http://127.0.0.1:{server.server_port}/#dashboard',wait_until='networkidle',timeout=20000)
            assert response and response.status==200
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v45-gallery-touch-targets')",timeout=15000)
            await page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000)
            result['before']={'status':response.status,'cacheKeys':await page.evaluate('caches.keys()'),'projects':await page.locator('.project-card').count(),'controller':await page.evaluate('navigator.serviceWorker.controller.scriptURL')}
            await page.locator('nav [data-view="projects"]:visible').click()
            await page.locator('[data-action="new-project"]:visible').first.click()
            form=page.locator('#project-form')
            await form.locator('[name="title"]').fill('QA v45 to v46 offline')
            await form.locator('[name="description"]').fill('Isolated service worker migration and local data retention check.')
            await form.locator('[name="created_at"]').fill('2026-10-30')
            await form.locator('[type="submit"]').click()
            await page.get_by_text('QA v45 to v46 offline',exact=True).first.wait_for(timeout=10000)
            result['before']['testRecordSaved']=True
            for src in NEW_WEB.rglob('*'):
                if src.is_file() and src.name!='sw.js':
                    dst=SITE/src.relative_to(NEW_WEB);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            shutil.copy2(NEW_WEB/'sw.js',SITE/'sw.js');(SITE/'sw.js').touch()
            assert 'folio-shell-v46-sidebar-secondary-text' in (SITE/'sw.js').read_text(encoding='utf-8')
            Handler.requests.clear()
            change=await page.evaluate("async()=>{const r=await navigator.serviceWorker.getRegistration();const c=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));await r.update();return Promise.race([c,new Promise(resolve=>setTimeout(()=>resolve(false),12000))])}")
            cache=[]
            for _ in range(80):
                cache=await page.evaluate('caches.keys()')
                if cache==['folio-shell-v46-sidebar-secondary-text']: break
                await page.wait_for_timeout(250)
            else: raise AssertionError({'cacheUpgradeTimeout':cache,'requests':Handler.requests})
            await page.wait_for_function("navigator.serviceWorker.controller?.scriptURL.includes('sw.js')")
            result['after']={'cacheKeys':cache,'controllerChange':change,'recordVisible':await page.get_by_text('QA v45 to v46 offline',exact=True).count(),'controller':await page.evaluate('navigator.serviceWorker.controller.scriptURL'),'requestedServiceWorker':any('sw.js' in x for x in Handler.requests)}
            assert change and result['after']['recordVisible']==1 and result['after']['requestedServiceWorker']
            await page.reload(wait_until='domcontentloaded',timeout=12000)
            await page.get_by_text('QA v45 to v46 offline',exact=True).first.wait_for(timeout=10000)
            result['after']['sidebarLabels']={}
            measure="""el=>{const fg=getComputedStyle(el).color,bg=getComputedStyle(el.closest('.sidebar')).backgroundColor,values=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number),l=x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4},a=values(fg),b=values(bg),la=.2126*l(a[0])+.7152*l(a[1])+.0722*l(a[2]),lb=.2126*l(b[0])+.7152*l(b[1])+.0722*l(b[2]);return{text:el.textContent.trim(),foreground:fg,background:bg,contrast:+((Math.max(la,lb)+.05)/(Math.min(la,lb)+.05)).toFixed(2)}}"""
            for theme in ('light','dark'):
                await page.evaluate('(theme)=>{document.documentElement.dataset.theme=theme}',theme)
                result['after']['sidebarLabels'][theme]=await page.locator('.workspace-label,.nav-count,.nav-external').evaluate_all('(els)=>els.filter(el=>el.getClientRects().length>0).map(el=>{const fg=getComputedStyle(el).color,bg=getComputedStyle(el.closest(".sidebar")).backgroundColor,values=s=>s.match(/[\\d.]+/g).slice(0,3).map(Number),l=x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4},a=values(fg),b=values(bg),la=.2126*l(a[0])+.7152*l(a[1])+.0722*l(a[2]),lb=.2126*l(b[0])+.7152*l(b[1])+.0722*l(b[2]);return{text:el.textContent.trim(),foreground:fg,background:bg,contrast:+((Math.max(la,lb)+.05)/(Math.min(la,lb)+.05)).toFixed(2)}})')
                assert result['after']['sidebarLabels'][theme] and any(item['text']=='МЕНЮ' for item in result['after']['sidebarLabels'][theme]),result['after']['sidebarLabels'][theme]
                assert all(item['contrast']>=4.5 for item in result['after']['sidebarLabels'][theme]),result['after']['sidebarLabels'][theme]
            await page.evaluate("()=>{document.documentElement.dataset.theme='light'}")
            await context.set_offline(True)
            await page.reload(wait_until='domcontentloaded',timeout=12000)
            await page.get_by_text('QA v45 to v46 offline',exact=True).first.wait_for(timeout=10000)
            result['offline']=await page.evaluate("()=>({recordVisible:document.body.innerText.includes('QA v45 to v46 offline'),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth})")
            result['offline']['cacheKeys']=await page.evaluate('caches.keys()')
            await page.screenshot(path=str(QA/'web-e2e-sw-upgrade-v45-v46-offline-1440x900.png'))
            assert result['offline']['recordVisible'] and result['offline']['cacheKeys']==['folio-shell-v46-sidebar-secondary-text'] and result['offline']['documentWidth']==result['offline']['viewportWidth']
            await page.set_viewport_size({'width':390,'height':844});await page.reload(wait_until='domcontentloaded',timeout=12000)
            await page.get_by_text('QA v45 to v46 offline',exact=True).first.wait_for(timeout=10000)
            result['offlineMobile']=await page.evaluate("()=>({recordVisible:document.body.innerText.includes('QA v45 to v46 offline'),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth})")
            await page.screenshot(path=str(QA/'web-e2e-sw-upgrade-v45-v46-offline-390x844.png'))
            assert result['offlineMobile']['recordVisible'] and result['offlineMobile']['documentWidth']==result['offlineMobile']['viewportWidth']
            await context.set_offline(False)
            assert not result['errors'],result['errors']
            await browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2);shutil.rmtree(TEMP,ignore_errors=True)
    (QA/'web-e2e-sw-upgrade-v45-v46-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))
if __name__=='__main__': asyncio.run(main())



