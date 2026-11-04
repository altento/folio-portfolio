from __future__ import annotations
import asyncio,json,shutil,tempfile,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
QA=Path(__file__).resolve().parent
WEB=QA.parent/'02_Приложение'/'web'
OLD=QA/'fixtures'/'sw-upgrade-v53-v54'/'web-v53'
TEMP=Path(tempfile.mkdtemp(prefix='folio-v53-v54-update-'))
SITE=TEMP/'site'
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
 def log_message(self,*_args):pass
async def main():
 shutil.copytree(WEB,SITE)
 for name in ('index.html','app.js','core.js','styles.css','sw.js'):shutil.copy2(OLD/name,SITE/name)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)));threading.Thread(target=server.serve_forever,daemon=True).start()
 result={'migration':{},'data':{},'errors':[]}
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check'])
   context=await browser.new_context(viewport={'width':1440,'height':900},service_workers='allow');page=await context.new_page()
   page.on('pageerror',lambda error:result['errors'].append(str(error)));page.on('console',lambda msg:result['errors'].append(msg.text) if msg.type=='error' else None)
   await page.goto(f'http://127.0.0.1:{server.server_port}/#dashboard',wait_until='networkidle',timeout=20000)
   await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v53-saved-filter-views')",timeout=15000)
   await page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);await page.reload(wait_until='networkidle',timeout=20000)
   await page.locator('nav [data-view="projects"]:visible').click()
   result['data']['demoProjectsLoadedBeforeUpdate']=await page.locator('.project-card').count()==3
   await page.locator('#search-input').fill('CRM')
   await page.locator('[data-action="save-filter-view"]').click();await page.locator('#saved-filter-name').fill('CRM до обновления');await page.locator('#saved-filter-form button[type="submit"]').click()
   result['data']['savedFilterCreatedBeforeUpdate']=await page.locator('#saved-filter-view option').count()==2
   await page.locator('#search-input').fill('')
   await page.screenshot(path=str(QA/'web-update-v53-v54-notice-1440x900.png'))
   for src in WEB.rglob('*'):
    if src.is_file():
     dst=SITE/src.relative_to(WEB);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   (SITE/'sw.js').touch()
   changed=await page.evaluate("""async()=>{const registration=await navigator.serviceWorker.getRegistration();const change=new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',()=>resolve(true),{once:true}));await registration.update();return Promise.race([change,new Promise(resolve=>setTimeout(()=>resolve(false),15000))])}""")
   await page.locator('#update-notice').wait_for(state='visible',timeout=10000)
   result['migration'].update({'controllerChanged':changed,'noticeVisible':await page.locator('#update-notice').is_visible()})
   assert changed and result['migration']['noticeVisible'],result
   await page.locator('#update-reload').click();await page.wait_for_load_state('domcontentloaded',timeout=12000)
   await page.locator('#update-notice').wait_for(state='hidden',timeout=10000)
   await page.wait_for_function("async()=>{const keys=await caches.keys();return keys.length===1&&keys[0]==='folio-shell-v54-bulk-actions'}",timeout=15000)
   await page.locator('nav [data-view="projects"]:visible').click();result['data']['projectsRetained']=await page.locator('.project-card').count()==3
   result['migration']['savedFilterRetained']=await page.locator('#saved-filter-view option').count()==2
   await page.locator('#saved-filter-view').select_option(label='CRM до обновления')
   result['data']['savedFilterStillApplies']=await page.locator('#search-input').input_value()=='CRM' and await page.locator('.project-card').count()==1
   await page.locator('#reset-filters').click();await page.locator('#select-visible-projects').check();await page.locator('[data-bulk="feature"]').click()
   await page.get_by_text('Выбранные проекты добавлены в избранное.').wait_for(timeout=5000)
   result['migration']['v54BulkActionsAvailableAfterUpdate']=await page.locator('[data-bulk="unfeature"]').count()==1
   await page.screenshot(path=str(QA/'web-update-v54-bulk-actions-1440x900.png'),full_page=True)
   await context.set_offline(True);await page.reload(wait_until='domcontentloaded',timeout=12000);await page.locator('nav [data-view="projects"]:visible').click()
   result['data']['projectsRetainedOffline']=await page.locator('.project-card').count()==3
   result['migration']['savedFilterAvailableOffline']=await page.locator('#saved-filter-view option').count()==2
   result['migration']['cacheKeys']=await page.evaluate('caches.keys()')
   result['migration']['cacheKeysOnlyV54']=result['migration']['cacheKeys']==['folio-shell-v54-bulk-actions']
   assert all(result['data'].values()) and all(value for key,value in result['migration'].items() if key!='cacheKeys'),result
   assert not result['errors'],result['errors']
   await context.set_offline(False);await browser.close()
 finally:server.shutdown();server.server_close()
 (QA/'web-update-v53-v54-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
