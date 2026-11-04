from playwright.sync_api import sync_playwright
from pathlib import Path
import json
OUT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8765/#dashboard'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    rows=[]
    for name,w,h in [('desktop',1440,900),('mobile',390,844)]:
        page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
        errors=[]; page.on('pageerror',lambda error: errors.append(str(error)))
        response=page.goto(URL,wait_until='networkidle',timeout=20000)
        page.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=Math.max(300,innerHeight*.75)){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,120))}window.scrollTo(0,0);await new Promise(r=>setTimeout(r,500))}")
        imgs=page.locator('img').evaluate_all('(xs)=>xs.map(x=>({src:x.currentSrc||x.src,loaded:x.complete&&x.naturalWidth>0,naturalWidth:x.naturalWidth}))')
        filename=OUT/f'portfolio-live-final-{name}-{w}x{h}.png'
        page.screenshot(path=str(filename),full_page=True)
        rows.append({'viewport':name,'httpStatus':response.status if response else None,'title':page.title(),'route':page.evaluate('location.hash'),'overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth'),'pageErrors':errors,'images':imgs,'imageFailures':[x for x in imgs if not x['loaded']],'screenshot':filename.name})
        page.close()
    browser.close()
(OUT/'portfolio-live-final-snapshot-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))

