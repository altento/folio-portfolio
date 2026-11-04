from __future__ import annotations
import asyncio, json, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright

PKG=Path(__file__).resolve().parents[1]
WEB=PKG/'02_Приложение'/'web'
OUT=PKG/'04_QA_доказательства'/'web-v66-clean-pwa-install'
OUT.mkdir(parents=True,exist_ok=True)
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
async def main():
 if not CHROME.exists(): raise RuntimeError(f'Chrome not found: {CHROME}')
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(WEB)))
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f'http://127.0.0.1:{server.server_port}/'
 result={'date':'2026-11-01','purpose':'fresh mobile context; PWA metadata, dashboard safe-area layout, offline relaunch','url':base,'fresh_context':True,'errors':[]}
 try:
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check'])
   context=await browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True,service_workers='allow')
   page=await context.new_page();page.on('pageerror',lambda e:result['errors'].append(str(e)))
   page.on('console',lambda m:result['errors'].append(m.text) if m.type=='error' else None)
   await page.goto(base,wait_until='networkidle',timeout=30000)
   await page.wait_for_function("'serviceWorker' in navigator && navigator.serviceWorker.controller",timeout=20000)
   await page.evaluate("navigator.serviceWorker.ready")
   await page.wait_for_timeout(400)
   online=await page.evaluate("""async()=>{
     const link=document.querySelector('link[rel=manifest]');const manifest=await (await fetch(link.href)).json();
     const reg=await navigator.serviceWorker.ready;const cacheNames=await caches.keys();
     const cache=await caches.open(cacheNames.find(n=>n.startsWith('folio-shell-'))||'missing');
     const precache=await cache.keys();
     const icons=await Promise.all(manifest.icons.map(async i=>{const r=await fetch(new URL(i.src,link.href));let dims=null;if(i.type==='image/png'){const b=await r.blob();const im=await createImageBitmap(b);dims=[im.width,im.height];im.close()}return {src:i.src,status:r.status,type:i.type,sizes:i.sizes,dims}}));
     return {secure:window.isSecureContext,serviceWorkerState:reg.active?.state||null,controlled:Boolean(navigator.serviceWorker.controller),cacheNames,precacheCount:precache.length,manifest:{name:manifest.name,short_name:manifest.short_name,display:manifest.display,start_url:manifest.start_url,scope:manifest.scope,icons:manifest.icons},icons,heading:document.querySelector('h1')?.innerText||'',demoVisible:Boolean(document.querySelector('.demo-note')),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,bodyText:document.body.innerText.slice(0,300)};
   }""")
   layout=await page.evaluate("""()=>{const nav=document.querySelector('.mobile-nav')?.getBoundingClientRect(),stats=document.querySelector('.editorial-stat-grid')?.getBoundingClientRect(),hero=document.querySelector('.dashboard-hero-editorial')?.getBoundingClientRect(),demo=document.querySelector('.demo-note')?.getBoundingClientRect(),cards=[...document.querySelectorAll('.editorial-stat-grid .stat-card')].map(x=>{const r=x.getBoundingClientRect();return {top:r.top,bottom:r.bottom}});return {nav:nav&&{top:nav.top,bottom:nav.bottom},stats:stats&&{top:stats.top,bottom:stats.bottom},statCards:cards,hero:hero&&{top:hero.top,bottom:hero.bottom},demo:demo&&{top:demo.top,bottom:demo.bottom},statsNavOverlap:Boolean(nav&&cards.some(card=>card.bottom>nav.top&&card.top<nav.bottom)),statsBeforeDemo:Boolean(stats&&demo&&demo.top>=stats.bottom)}}""")
   online['dashboard_layout']=layout
   await page.screenshot(path=str(OUT/'pwa-fresh-first-screen-390x844.png'),full_page=False)
   await page.screenshot(path=str(OUT/'pwa-fresh-first-launch-390x844.png'),full_page=True)
   await page.set_viewport_size({'width':320,'height':568})
   await page.evaluate("()=>{const node=document.querySelector('.editorial-stat-grid');window.scrollTo(0,node.getBoundingClientRect().top+window.scrollY-72)}")
   await page.wait_for_timeout(150)
   compact_layout=await page.evaluate("()=>{const nav=document.querySelector('.mobile-nav')?.getBoundingClientRect(),cards=[...document.querySelectorAll('.editorial-stat-grid .stat-card')].map(x=>{const r=x.getBoundingClientRect();return {top:r.top,bottom:r.bottom}});return {documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,navTop:nav?.top,cardCount:cards.length,cards,allCardsAboveNav:Boolean(nav&&cards.length===4&&cards.every(card=>card.top>=0&&card.bottom<=nav.top))}}")
   result['mobile_320_metrics']=compact_layout
   await page.screenshot(path=str(OUT/'pwa-metrics-320x568.png'),full_page=False)
   await page.set_viewport_size({'width':390,'height':844});await page.evaluate('window.scrollTo(0,0)')
   await context.set_offline(True)
   await page.reload(wait_until='networkidle',timeout=30000)
   await page.wait_for_timeout(300)
   offline=await page.evaluate("""()=>({online:navigator.onLine,controller:Boolean(navigator.serviceWorker.controller),heading:document.querySelector('h1')?.innerText||'',demoVisible:Boolean(document.querySelector('.demo-note')),projectCards:document.querySelectorAll('.project-card').length,documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,fatal:Boolean(document.querySelector('.fatal-state')),bodyText:document.body.innerText.slice(0,300)})""")
   await page.screenshot(path=str(OUT/'pwa-fresh-offline-relaunch-390x844.png'),full_page=True)
   result['online_first_launch']=online;result['offline_relaunch']=offline
   result['confirmed']=bool(online['secure'] and online['serviceWorkerState']=='activated' and online['controlled'] and online['precacheCount']>=15 and any(name=='folio-shell-v66-mobile-dashboard-safe-area' for name in online['cacheNames']) and online['dashboard_layout']['statsBeforeDemo'] and not online['dashboard_layout']['statsNavOverlap'] and online['manifest']['display']=='standalone' and online['manifest']['name'] and online['manifest']['short_name'] and len(online['icons'])>=2 and all(i['status']==200 for i in online['icons']) and online['icons'][0]['dims']==[192,192] and online['icons'][1]['dims']==[512,512] and online['demoVisible'] and online['documentWidth']==online['viewportWidth'] and result['mobile_320_metrics']['documentWidth']==320 and result['mobile_320_metrics']['allCardsAboveNav'] and offline['online'] is False and offline['controller'] and offline['demoVisible'] and offline['projectCards']>=3 and not offline['fatal'] and offline['documentWidth']==offline['viewportWidth'] and not result['errors'])
   result['screenshots']=['pwa-fresh-first-screen-390x844.png','pwa-fresh-first-launch-390x844.png','pwa-metrics-320x568.png','pwa-fresh-offline-relaunch-390x844.png']
   await context.close();await browser.close()
 finally:
  server.shutdown();server.server_close()
 (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if not result.get('confirmed'): raise SystemExit('Clean PWA first launch/offline relaunch verification failed')
if __name__=='__main__': asyncio.run(main())
