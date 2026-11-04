from __future__ import annotations
import asyncio, json, shutil, tempfile, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

QA=Path(__file__).resolve().parent
WEB=QA.parent/'02_Приложение'/'web'
TEMP=Path(tempfile.mkdtemp(prefix='folio-saved-view-layout-v82-'))
SITE=TEMP/'site'
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def log_message(self,*args): pass
async def main():
    shutil.copytree(WEB,SITE)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    result={'version':'web-pwa-v83-saved-view-touch-targets','checks':{},'errors':[],'externalOrigins':[],'externalRequestDetails':[],'screenshots':[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check','--disable-extensions','--disable-component-extensions-with-background-pages'])
        context=await browser.new_context(viewport={'width':1440,'height':900},service_workers='allow')
        page=await context.new_page()
        page.on('pageerror',lambda e:result['errors'].append(str(e)))
        page.on('console',lambda m:result['errors'].append(m.text) if m.type=='error' else None)
        def record_request(q):
            if '127.0.0.1' not in q.url and 'localhost' not in q.url and not q.url.startswith('data:'):
                origin=q.url.split('/')[0]+'//'+q.url.split('/')[2]
                result['externalOrigins'].append(origin)
                try: frame_origin=q.frame.url.split('/')[0]+'//'+q.frame.url.split('/')[2]
                except Exception: frame_origin='unavailable'
                result['externalRequestDetails'].append({'origin':origin,'resourceType':q.resource_type,'frameOrigin':frame_origin})
        page.on('request',record_request)
        response=await page.goto(f'http://127.0.0.1:{server.server_port}/#dashboard',wait_until='networkidle',timeout=20000)
        result['checks']['initialLoad']=bool(response and response.status==200)
        result['externalScriptElements']=await page.evaluate("() => Array.from(document.scripts).filter(s=>s.src && new URL(s.src).origin!==location.origin).map(s=>({origin:new URL(s.src).origin,scriptName:new URL(s.src).pathname.split('/').at(-1)}))")
        await page.wait_for_function("async()=>navigator.serviceWorker.controller!==null",timeout=15000)
        result['checks']['v83ServiceWorkerActive']=await page.evaluate("async()=>{const keys=await caches.keys();return keys.includes('folio-shell-v83-mobile-touch-targets')}")
        await page.locator('nav [data-view="projects"]:visible').click()
        await page.locator('#search-input').fill('CRM')
        await page.locator('#filter-type').select_option(label='Веб-приложение')
        await page.locator('#filter-status').select_option(label='В разработке')
        await page.locator('#filter-tag').select_option(label='CRM')
        await page.locator('#sort-projects').select_option('newest')
        await page.locator('[data-layout-choice="list"]').click()
        result['checks']['filteredSingleResultInList']=await page.locator('.project-card').count()==1 and await page.locator('.project-grid').evaluate("e=>e.classList.contains('project-list')")
        await page.locator('[data-action="save-filter-view"]').click()
        await page.locator('#saved-filter-name').fill('CRM список v82')
        await page.locator('#saved-filter-form button[type="submit"]').click()
        saved=json.loads(await page.evaluate("localStorage.getItem('folio-saved-filter-views-v1')"))
        result['checks']['layoutPersistedInSavedSnapshot']=saved[0]['filters'].get('layout')=='list'
        result['checks']['savedViewControlsHaveAccessibleNames']=await page.get_by_role('combobox',name='Сохранённые представления').count()==1 and await page.get_by_role('button',name='Сохранить вид').count()==1 and await page.get_by_role('button',name='Удалить выбранное представление').count()==1
        await page.locator('[data-layout-choice="cards"]').click()
        await page.locator('#reset-filters').click()
        await page.locator('#saved-filter-view').select_option(label='CRM список v82')
        result['checks']['applyRestoresAllFiltersAndLayout']=await page.locator('#search-input').input_value()=='CRM' and await page.locator('#filter-type').input_value()=='Веб-приложение' and await page.locator('#filter-status').input_value()=='В разработке' and await page.locator('#filter-tag').input_value()=='CRM' and await page.locator('#sort-projects').input_value()=='newest' and await page.locator('.project-card').count()==1 and await page.locator('.project-grid').evaluate("e=>e.classList.contains('project-list')")
        result['checks']['globalLayoutPreferenceUpdated']=await page.evaluate("localStorage.getItem('folio-project-layout')==='list'")
        await page.keyboard.press('Tab')
        result['checks']['savedViewKeyboardFocusVisible']=await page.evaluate("document.activeElement.matches(':focus-visible') && getComputedStyle(document.activeElement).outlineStyle!=='none' && parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=2")
        await page.locator('#toast-region .toast').wait_for(state='hidden',timeout=6000)
        await page.screenshot(path=str(QA/'saved-view-layout-desktop-1440x900-2026-11-01.jpg'))
        result['screenshots'].append('saved-view-layout-desktop-1440x900-2026-11-01.jpg')
        for width,height in ((390,844),(320,568)):
            await page.set_viewport_size({'width':width,'height':height})
            result['checks'][f'noHorizontalOverflow-{width}']=await page.evaluate('document.documentElement.scrollWidth===innerWidth')
            targets=await page.locator('.saved-views select,.saved-views .button').evaluate_all("els=>els.map(e=>({name:e.getAttribute('aria-label')||e.textContent.trim(),height:e.getBoundingClientRect().height}))")
            result.setdefault('mobileTargetsByWidth',{})[str(width)]=targets
            result['checks'][f'savedViewTargetsAtLeast44px-{width}']=all(t['height']>=44 for t in targets)
            if width==390:
                result['mobileTargets']=targets
            if width==390:
                await page.locator('.saved-views').scroll_into_view_if_needed()
                await page.locator('#toast-region .toast').wait_for(state='hidden',timeout=6000)
                await page.screenshot(path=str(QA/'saved-view-layout-mobile-390x844-2026-11-01.jpg'))
                result['screenshots'].append('saved-view-layout-mobile-390x844-2026-11-01.jpg')
        await page.reload(wait_until='networkidle')
        await page.locator('nav [data-view="projects"]:visible').click()
        result['checks']['savedViewPersistsReload']=await page.locator('#saved-filter-view option').count()==2
        await page.context.set_offline(True)
        offline=await page.reload(wait_until='domcontentloaded',timeout=15000)
        await page.locator('nav [data-view="projects"]:visible').click()
        await page.locator('#saved-filter-view').wait_for(state='visible',timeout=10000)
        result['checks']['offlineReloadWithSavedView']=bool(offline and offline.status==200) and await page.locator('#saved-filter-view option').count()==2
        await page.context.set_offline(False)
        legacy={'id':'legacy','name':'Legacy without layout','filters':{'query':'CRM','type':'Веб-приложение','status':'В разработке','tag':'CRM','sort':'newest','featuredOnly':False}}
        await page.evaluate("v=>{localStorage.setItem('folio-project-layout','cards');localStorage.setItem('folio-saved-filter-views-v1',JSON.stringify([v]))}",legacy)
        await page.reload(wait_until='networkidle')
        await page.locator('nav [data-view="projects"]:visible').click()
        await page.locator('#saved-filter-view').select_option(label='Legacy without layout')
        result['checks']['legacyViewKeepsCurrentLayout']=await page.locator('.project-grid').evaluate("e=>!e.classList.contains('project-list')") and await page.evaluate("localStorage.getItem('folio-project-layout')==='cards'")
        result['errors']=list(dict.fromkeys(result['errors']))
        result['checks']['noPageOrConsoleErrors']=len(result['errors'])==0
        # The app source has no remote script, font, API or analytics URL. Chrome may
        # emit a request from a host security/network-filter component; preserve it
        # as an observation instead of silently claiming zero outbound traffic.
        result['observedThirdPartyOrigins']=sorted(set(result['externalOrigins']))
        assert all(result['checks'].values()),json.dumps(result,ensure_ascii=False,indent=2)
        await browser.close()
    server.shutdown();server.server_close()
    (QA/'saved-view-layout-e2e-2026-11-01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': asyncio.run(main())
