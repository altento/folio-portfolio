from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path(__file__).resolve().parent
URL='https://altento.github.io/folio-portfolio/?qa=v120-cross-route'
VIEWS={'dashboard':None,'projects':'Мои проекты','showcase':'Витрина','settings':'Настройки и данные'}
SIZES={'desktop':(1440,900),'mobile':(390,844)}
def main():
    results=[]; errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        for device,(w,h) in SIZES.items():
            context=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1,service_workers='allow')
            page=context.new_page(); page.set_default_timeout(15000)
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.on('console',lambda m: errors.append(m.text) if m.type=='error' else None)
            response=page.goto(URL,wait_until='networkidle',timeout=45000)
            assert response and response.status==200, f'HTTP {response.status if response else None}'
            page.wait_for_timeout(1000)
            for view,label in VIEWS.items():
                if label:
                    page.locator(f'[data-view="{view}"]:visible').first.click()
                    page.wait_for_timeout(250)
                # Trigger lazy images before taking a full-page capture.
                page.evaluate("async()=>{const imgs=[...document.images];for(const i of imgs){i.scrollIntoView({block:'center'});await new Promise(r=>requestAnimationFrame(r));try{await i.decode()}catch{}}window.scrollTo(0,0)}")
                page.wait_for_timeout(150)
                metrics=page.evaluate("()=>({title:document.querySelector('#page-title')?.innerText||document.title,hash:location.hash,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,viewport:innerWidth,images:[...document.images].map(i=>({src:i.currentSrc,ok:i.complete&&i.naturalWidth>0})),hiddenLabels:[...document.querySelectorAll('.cover-kicker,.cover-index')].every(x=>x.getAttribute('aria-hidden')==='true')})")
                filename=f'web-v120-{device}-{view}.png'; page.screenshot(path=str(OUT/filename),full_page=True,animations='disabled')
                results.append({'device':device,'view':view,'viewport':[w,h],**metrics,'horizontalOverflow':metrics['width']>w,'imagesBroken':[i['src'] for i in metrics['images'] if not i['ok']],'screenshot':filename})
            context.close()
        browser.close()
    payload={'url':URL,'version':'v120','commit':'94dbdb2','checks':results,'page_or_console_errors':errors,'passed':len(results)==8 and not errors and all(not x['horizontalOverflow'] and not x['imagesBroken'] and x['hiddenLabels'] for x in results)}
    (OUT/'results-v120.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(results),'passed':payload['passed'],'errors':errors,'overflows':[x['device']+'/'+x['view'] for x in results if x['horizontalOverflow']],'broken_images':[x['device']+'/'+x['view'] for x in results if x['imagesBroken']]},ensure_ascii=False))
    if not payload['passed']: raise SystemExit(1)
if __name__=='__main__': main()
