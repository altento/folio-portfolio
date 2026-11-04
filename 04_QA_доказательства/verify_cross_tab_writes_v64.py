from __future__ import annotations
import asyncio
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE = SCRIPT_DIR.parent
WEB = PACKAGE / '02_Приложение' / 'web'
OUT = SCRIPT_DIR / 'web-v64-indexeddb-write-conflict'
OUT.mkdir(parents=True, exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

async def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    results = {'date':'2026-11-01','version':'folio-shell-v64-indexeddb-write-conflicts','errors':[]}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', args=['--no-first-run','--no-default-browser-check','--disable-extensions'])
            context = await browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, service_workers='block')
            first, second = await context.new_page(), await context.new_page()
            first.on('pageerror', lambda error: results['errors'].append(f'first: {error}'))
            second.on('pageerror', lambda error: results['errors'].append(f'second: {error}'))
            await asyncio.gather(first.goto(url, wait_until='domcontentloaded'), second.goto(url, wait_until='domcontentloaded'))
            await asyncio.gather(first.locator('.project-card').first.wait_for(state='visible'), second.locator('.project-card').first.wait_for(state='visible'))
            results['simultaneous_startup'] = {'both_tabs_loaded':True,'fatal_states':await asyncio.gather(first.locator('.fatal-state').count(), second.locator('.fatal-state').count())}

            await second.locator('[data-view="settings"]:visible').first.click()
            await second.locator('input[name="full_name"]').fill('Проверка вкладки Б')
            await second.locator('#profile-form button[type="submit"], #profile-form button:not([type])').click()
            await second.wait_for_function("async () => { const {IndexedPortfolioStore}=await import('./core.js'); const r=await new IndexedPortfolioStore().getRecord(); return r.value?.developer?.full_name==='Проверка вкладки Б' && r.revision>=2 }", timeout=10000)
            second_record = await second.evaluate("async () => { const {IndexedPortfolioStore}=await import('./core.js'); const r=await new IndexedPortfolioStore().getRecord(); return {name:r.value.developer.full_name,revision:r.revision} }")

            await first.locator('[data-view="settings"]:visible').first.click()
            await first.locator('input[name="full_name"]').fill('Устаревшее значение вкладки А')
            await first.locator('#profile-form button[type="submit"], #profile-form button:not([type])').click()
            await first.wait_for_function("document.querySelector('#profile-form-error')?.textContent.includes('Данные уже изменились в другой вкладке')", timeout=10000)
            error_text = (await first.locator('#profile-form-error').inner_text()).strip()
            latest = await first.evaluate("async () => { const {IndexedPortfolioStore}=await import('./core.js'); const r=await new IndexedPortfolioStore().getRecord(); return {name:r.value.developer.full_name,revision:r.revision} }")
            if latest['name'] != 'Проверка вкладки Б':
                raise AssertionError(f'Stale tab overwrote the latest record: {latest}')
            results['stale_tab_write'] = {'rejected':True,'user_message':error_text,'latest_record_preserved':latest,'winning_write':second_record}
            error = first.locator('#profile-form-error')
            await error.scroll_into_view_if_needed()
            await first.screenshot(path=str(OUT/'web-v64-cross-tab-conflict-390x844.png'))

            race = await first.evaluate("""async () => {
              const {IndexedPortfolioStore}=await import('./core.js');
              const name='folio-revision-race-'+crypto.randomUUID();
              const a=new IndexedPortfolioStore(name,'portfolio'), b=new IndexedPortfolioStore(name,'portfolio');
              const writes=await Promise.allSettled([a.put({writer:'A'},{expectedRevision:0}),b.put({writer:'B'},{expectedRevision:0})]);
              const record=await a.getRecord();
              const summary={fulfilled:writes.filter(x=>x.status==='fulfilled').length,rejected:writes.filter(x=>x.status==='rejected').length,conflictErrors:writes.filter(x=>x.status==='rejected'&&x.reason?.name==='PortfolioWriteConflictError').length,revision:record.revision,winner:record.value?.writer};
              a.dbPromise && (await a.dbPromise).close(); b.dbPromise && (await b.dbPromise).close();
              // Unique temporary database is isolated to this ephemeral browser context.
              return summary;
            }""")
            results['simultaneous_writes'] = race
            if race != {'fulfilled':1,'rejected':1,'conflictErrors':1,'revision':1,'winner':race['winner']} or race['winner'] not in ['A','B']:
                raise AssertionError(f'Atomic revision check failed: {race}')

            legacy = await first.evaluate("""async () => {
              const {IndexedPortfolioStore}=await import('./core.js');
              const name='folio-legacy-record-'+crypto.randomUUID();
              await new Promise((resolve,reject)=>{
                const request=indexedDB.open(name,1);
                request.onupgradeneeded=()=>request.result.createObjectStore('records',{keyPath:'key'});
                request.onerror=()=>reject(request.error);
                request.onsuccess=()=>{
                  const db=request.result,tx=db.transaction('records','readwrite');
                  tx.objectStore('records').put({key:'portfolio',value:{marker:'legacy-v63'}});
                  tx.oncomplete=()=>{db.close();resolve()};
                  tx.onerror=()=>reject(tx.error);
                };
              });
              const store=new IndexedPortfolioStore(name,'portfolio'),before=await store.getRecord();
              const revision=await store.put({...before.value,migrated:true},{expectedRevision:before.revision});
              const after=await store.getRecord();
              (await store.dbPromise).close();
              // Unique temporary database is isolated to this ephemeral browser context.
              return {legacyRevisionBefore:before.revision,legacyMarkerPreserved:after.value.marker==='legacy-v63',revisionAfterWrite:revision,migratedFlag:after.value.migrated===true};
            }""")
            results['legacy_record_compatibility'] = legacy
            if legacy != {'legacyRevisionBefore':0,'legacyMarkerPreserved':True,'revisionAfterWrite':1,'migratedFlag':True}:
                raise AssertionError(f'Legacy IndexedDB record compatibility failed: {legacy}')

            offline_context = await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow')
            offline_page = await offline_context.new_page()
            offline_page.on('pageerror',lambda error: results['errors'].append(f'offline: {error}'))
            await offline_page.goto(url,wait_until='domcontentloaded')
            await offline_page.locator('.project-card').first.wait_for(state='visible',timeout=15000)
            await offline_page.wait_for_function('!!navigator.serviceWorker.controller',timeout=15000)
            await offline_page.locator('[data-view="settings"]:visible').first.click()
            await offline_page.locator('input[name="full_name"]').fill('Офлайн-проверка v64')
            await offline_page.locator('#profile-form button[type="submit"], #profile-form button:not([type])').click()
            await offline_page.wait_for_function("async () => { const {IndexedPortfolioStore}=await import('./core.js'); const r=await new IndexedPortfolioStore().getRecord(); return r.value?.developer?.full_name==='Офлайн-проверка v64' }")
            before_offline = await offline_page.evaluate("async () => ({controller:navigator.serviceWorker.controller?.scriptURL||'',caches:(await caches.keys()).filter(key=>key.startsWith('folio-shell-'))})")
            await offline_context.set_offline(True)
            await offline_page.reload(wait_until='domcontentloaded',timeout=15000)
            await offline_page.locator('.project-card').first.wait_for(state='visible',timeout=15000)
            await offline_page.locator('[data-view="settings"]:visible').first.click()
            persisted = await offline_page.locator('input[name="full_name"]').input_value()
            if persisted != 'Офлайн-проверка v64' or not any('v64-indexeddb-write-conflicts' in key for key in before_offline['caches']):
                raise AssertionError(f'Offline v64 reload did not preserve installed shell/data: {before_offline}, name={persisted!r}')
            results['offline_reload'] = {'controller':before_offline['controller'],'cache_names':before_offline['caches'],'reload_succeeded':True,'profile_preserved':persisted}
            await offline_page.screenshot(path=str(OUT/'web-v64-offline-mobile-390x844.png'))
            await offline_context.close()
            if results['errors']:
                raise AssertionError(f'Browser runtime errors: {results["errors"]}')
            await context.close()
            await browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (OUT/'web-v64-indexeddb-write-conflict-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    asyncio.run(main())
