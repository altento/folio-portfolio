import asyncio, json, shutil, tempfile, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
SCRIPT_DIR=Path(__file__).resolve().parent; ROOT=SCRIPT_DIR.parents[1]; PACKAGE=ROOT/'Пакет_сдачи_портфолио_модули_4_5_на_проверку'; OLD_WEB=PACKAGE/'02_Приложение'/'web'; FIXTURE=PACKAGE/'04_QA_доказательства'/'fixtures'/'sw-upgrade-v59-v60'/'web-v59'; SOURCE_WEB=ROOT/'web'; NEW_WEB=SOURCE_WEB if SOURCE_WEB.is_dir() else OLD_WEB; QA=SCRIPT_DIR; TEMP=Path(tempfile.mkdtemp(prefix='folio-sw-v59-v60-')); SITE=TEMP/'site'; CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self): self.send_header('Cache-Control','no-store'); super().end_headers()
 def log_message(self,*args): pass
async def read_ids(page): return await page.evaluate("""async()=>new Promise((resolve,reject)=>{const r=indexedDB.open('folio-workspace',1);r.onsuccess=()=>{const q=r.result.transaction('records','readonly').objectStore('records').get('portfolio');q.onsuccess=()=>resolve((q.result?.value?.projects||[]).map(p=>p.id));q.onerror=()=>reject(q.error)};r.onerror=()=>reject(r.error)})""")
async def main():
 shutil.copytree(OLD_WEB,SITE);
 for f in ('app.js','sw.js','demo.json'): shutil.copy2(FIXTURE/f,SITE/f)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE))); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}/'; result={'from':'folio-shell-v59-editorial-portfolio-dashboard','to':'folio-shell-v60-editorial-case-art','checks':{},'errors':[]}
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check']);ctx=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow');page=await ctx.new_page();page.on('pageerror',lambda e:result['errors'].append(str(e)));page.on('console',lambda m:result['errors'].append(m.text) if m.type=='error' else None)
   await page.goto(base+'#dashboard',wait_until='networkidle',timeout=25000);await page.wait_for_function("navigator.serviceWorker.controller!==null");await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v59-editorial-portfolio-dashboard')");await page.reload(wait_until='networkidle');ids_before=await read_ids(page);result['checks']['legacyShellAndIndexedDBReady']=len(ids_before)==3
   for f in ('app.js','sw.js','demo.json'):shutil.copy2(NEW_WEB/f,SITE/f)
   for f in ('cleaning-crm-case-v2.webp','city-courtyards-case-v2.webp'):shutil.copy2(NEW_WEB/'assets'/'covers'/f,SITE/'assets'/'covers'/f)
   await page.evaluate('navigator.serviceWorker.ready.then(r=>r.update())');await page.wait_for_selector('#update-notice:not([hidden])',timeout=15000);await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v60-editorial-case-art')",timeout=15000);result['checks']['newAssetsCachedBeforeConfirmation']=await page.evaluate("async()=> (await caches.keys()).includes('folio-shell-v60-editorial-case-art')")
   await page.screenshot(path=str(QA/'web-update-v59-v60-notice-mobile-390x844.png'),full_page=False,animations='disabled');await page.locator('#update-reload').click();await page.wait_for_load_state('networkidle');await page.wait_for_function("navigator.serviceWorker.controller?.scriptURL.includes('sw.js')");ids_after=await read_ids(page);result['checks']['indexedDbRecordsSurviveUpdate']=ids_after==ids_before
   keys=await page.evaluate("caches.keys().then(k=>k.filter(x=>x.startsWith('folio-shell-')))");result['checks']['oldCacheRemovedAndV60Active']=keys==['folio-shell-v60-editorial-case-art'];result['cacheKeysAfterUpdate']=keys
   await page.locator('.mobile-nav [data-view="projects"]').click();imgs=page.locator('.project-card img');await imgs.first.wait_for(state='visible');srcs=[]
   for i in range(await imgs.count()):
    img=imgs.nth(i);await img.scroll_into_view_if_needed();await img.evaluate("e=>e.decode()");srcs.append(await img.get_attribute('src'))
   result['cover_sources']=srcs;result['checks']['legacyCrmCoverMapsToNewArt']=any('cleaning-crm-case-v2.webp' in src for src in srcs);result['checks']['legacyCourtyardCoverMapsToNewArt']=any('city-courtyards-case-v2.webp' in src for src in srcs);result['checks']['allThreeCoversLoadOnline']=len(srcs)==3
   await ctx.set_offline(True);await page.reload(wait_until='domcontentloaded',timeout=20000);await page.locator('.dashboard-hero-editorial').wait_for(state='visible');await page.locator('.mobile-nav [data-view="projects"]').click();imgs=page.locator('.project-card img')
   offline=[]
   for i in range(await imgs.count()):
    img=imgs.nth(i);await img.scroll_into_view_if_needed();await img.evaluate('e=>e.decode()');offline.append(await img.get_attribute('src'))
   result['checks']['allThreeCoversLoadOffline']=len(offline)==3 and all('case-v2' in src or 'portfolio-studio' in src for src in offline);result['checks']['offlineAppAndCaseArt']=True;result['offline_cover_sources']=offline;result['document_width']=await page.evaluate('document.documentElement.scrollWidth')
   await page.screenshot(path=str(QA/'web-v60-case-art-offline-mobile-390x844.png'),full_page=False,animations='disabled');result['screens']=['web-update-v59-v60-notice-mobile-390x844.png','web-v60-case-art-offline-mobile-390x844.png'];result['checks']['noApplicationErrors']=not result['errors'];assert all(result['checks'].values()),result
   await ctx.set_offline(False);await ctx.close();await browser.close()
 finally:
  server.shutdown();server.server_close();thread.join(timeout=2)
  shutil.rmtree(TEMP,ignore_errors=True)
 (QA/'web-update-v59-v60-case-art-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2))
asyncio.run(main())