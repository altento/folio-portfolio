from __future__ import annotations
import asyncio, json, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

QA=Path(__file__).resolve().parent
PACKAGE=QA.parent
WEB=PACKAGE/'02_Приложение'/'web'
OUT=QA/'web-v65-profile-conflict-recovery'
OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(WEB)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/'
 results={'date':'2026-11-01','version':'folio-shell-v65-profile-conflict-recovery','errors':[]}
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',args=['--no-first-run','--no-default-browser-check','--disable-extensions'])
   context=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='block')
   a,b=await context.new_page(),await context.new_page()
   a.on('pageerror',lambda e:results['errors'].append('tab A: '+str(e)))
   b.on('pageerror',lambda e:results['errors'].append('tab B: '+str(e)))
   await asyncio.gather(a.goto(url,wait_until='domcontentloaded'),b.goto(url,wait_until='domcontentloaded'))
   await asyncio.gather(a.locator('.project-card').first.wait_for(state='visible'),b.locator('.project-card').first.wait_for(state='visible'))
   await a.locator('[data-view="settings"]:visible').first.click()
   await b.locator('[data-view="settings"]:visible').first.click()
   await a.locator('input[name="email"]').fill('draft-a@example.test')
   await b.locator('input[name="full_name"]').fill('Актуальный профиль Б')
   await b.locator('#profile-form button:not([data-profile-latest])').click()
   await b.wait_for_function("async()=>{const {IndexedPortfolioStore}=await import('./core.js');return (await new IndexedPortfolioStore().get()).developer.full_name==='Актуальный профиль Б'}")
   await a.locator('#profile-form button:not([data-profile-latest])').click()
   await a.wait_for_function("document.querySelector('#profile-form-error')?.textContent.includes('Данные обновились в другой вкладке')")
   draft_preserved=await a.locator('input[name="email"]').input_value()
   differences=await a.locator('.profile-conflict-list').inner_text()
   if draft_preserved!='draft-a@example.test' or 'Актуальный профиль Б' not in differences:
    raise AssertionError(f'Profile conflict was not reviewable: draft={draft_preserved}, diff={differences}')
   await a.locator('#profile-form-error').scroll_into_view_if_needed()
   await a.screenshot(path=str(OUT/'web-v65-profile-conflict-390x844.png'),full_page=False)
   await a.set_viewport_size({'width':320,'height':568})
   responsive=await a.evaluate("() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,conflictButtons:[...document.querySelectorAll('[data-profile-latest]')].map(x=>({width:Math.round(x.getBoundingClientRect().width),height:Math.round(x.getBoundingClientRect().height)}))})")
   if responsive['document']>responsive['viewport'] or any(x['height']<44 for x in responsive['conflictButtons']): raise AssertionError(f'Mobile conflict layout failed: {responsive}')
   results['responsive_320x568']=responsive
   await a.screenshot(path=str(OUT/'web-v65-profile-conflict-320x568.png'),full_page=False)
   await a.set_viewport_size({'width':390,'height':844})
   await a.get_by_role('button',name='Взять сохранённое значение для Имя').click()
   latest_name=await a.locator('input[name="full_name"]').input_value()
   still_draft=await a.locator('input[name="email"]').input_value()
   if latest_name!='Актуальный профиль Б' or still_draft!='draft-a@example.test':
    raise AssertionError(f'Field-level resolution lost values: {latest_name}, {still_draft}')
   await a.locator('#profile-form button:not([data-profile-latest])').click()
   await a.wait_for_function("async()=>{const {IndexedPortfolioStore}=await import('./core.js');const r=await new IndexedPortfolioStore().getRecord();return r.value.developer.full_name==='Актуальный профиль Б'&&r.value.developer.email==='draft-a@example.test'}")
   saved=await a.evaluate("async()=>{const {IndexedPortfolioStore}=await import('./core.js');const r=await new IndexedPortfolioStore().getRecord();return {revision:r.revision,name:r.value.developer.full_name,email:r.value.developer.email,projectCount:r.value.projects.length}}")
   results['conflict_review']={'draft_preserved':draft_preserved,'saved_version_shown':True,'per_field_acceptance':True,'rebased_profile_saved':saved}
   results['page_errors']=results['errors']
   if results['errors']: raise AssertionError(results['errors'])
   await a.screenshot(path=str(OUT/'web-v65-profile-conflict-resolved-390x844.png'),full_page=True)
   (OUT/'web-v65-profile-conflict-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   await browser.close()
 finally: server.shutdown();server.server_close()
 print(json.dumps(results,ensure_ascii=False,indent=2))
asyncio.run(main())
