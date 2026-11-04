from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
FILES=sorted((ROOT/'fixtures'/'gallery-capacity-v44').glob('detail-*.png'))
URL='http://127.0.0.1:8765/#dashboard'
RESULTS=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    for name,w,h in [('desktop',1440,900),('mobile',390,844)]:
        context=browser.new_context(viewport={'width':w,'height':h},device_scale_factor=1)
        page=context.new_page();page.set_default_timeout(10000);print('START',name,flush=True);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        response=page.goto(URL,wait_until='networkidle',timeout=20000)
        page.evaluate('navigator.serviceWorker.ready')
        page.reload(wait_until='networkidle',timeout=20000)
        controlled=page.evaluate('Boolean(navigator.serviceWorker.controller)')
        page.locator('nav [data-view="projects"]:visible').click()
        page.locator('[data-action="new-project"]:visible').first.click()
        print('DIALOG',name,flush=True);page.locator('#project-dialog[open]').wait_for()
        print('UPLOAD',name,flush=True);page.locator('#gallery-files').set_input_files([{'name':f.name,'mimeType':'image/png','buffer':f.read_bytes()} for f in FILES])
        page.locator('.gallery-item').nth(7).wait_for(timeout=15000)
        print('EIGHT',name,flush=True);count=page.locator('.gallery-item').count()
        eighth=page.locator('.gallery-item-actions span').nth(7).inner_text()
        disabled=page.locator('#gallery-files').is_disabled()
        data_count=page.locator('#gallery-images-data').input_value()
        payload=json.loads(data_count)
        gallery_audit=page.locator('#gallery-editor').evaluate('''(root)=>{const controls=[...root.querySelectorAll('button,input:not([type=hidden])')].filter(el=>!el.classList.contains('visually-hidden'));return {controls:controls.map(el=>{const r=el.getBoundingClientRect(),label=el.getAttribute('aria-label')||el.getAttribute('title')||[...(el.labels||[])].map(x=>x.innerText).join(' ').trim()||el.innerText.trim();return {tag:el.tagName,type:el.type||null,name:label,width:Math.round(r.width),height:Math.round(r.height),disabled:el.disabled}}),unnamed:controls.filter(el=>!(el.getAttribute('aria-label')||el.getAttribute('title')||[...(el.labels||[])].some(x=>x.innerText.trim())||el.innerText.trim())).length,under44:controls.filter(el=>{const r=el.getBoundingClientRect();return r.width<44||r.height<44}).map(el=>({tag:el.tagName,type:el.type||null,name:el.getAttribute('aria-label')||el.innerText.trim(),width:Math.round(el.getBoundingClientRect().width),height:Math.round(el.getBoundingClientRect().height)}))}}''')
        page.locator('.gallery-item').nth(7).scroll_into_view_if_needed();page.screenshot(path=str(ROOT/f'gallery-capacity-v45-{name}-{w}x{h}.png'),full_page=False)
        RESULTS.append({'viewport':name,'httpStatus':response.status if response else None,'uploaded':count,'eighthLabel':eighth,'pickerDisabledAtLimit':disabled,'serializedItems':len(payload),'galleryAccessibility':gallery_audit,'aggregateDataUriChars':sum(len(x['image_data']) for x in payload),'serviceWorkerCacheKeys':page.evaluate('caches.keys()'), 'pageErrors':errors,'screenshot':f'gallery-capacity-v45-{name}-{w}x{h}.png'})
        page.keyboard.press('Escape')
        context.set_offline(True)
        offline_response=page.reload(wait_until='domcontentloaded',timeout=15000)
        page.locator('#main-content h1').wait_for(timeout=8000)
        RESULTS[-1]['serviceWorkerControlledBeforeOffline']=controlled
        RESULTS[-1]['offlineReloadStatus']=offline_response.status if offline_response else None
        RESULTS[-1]['offlineReloadVisibleHeading']=page.locator('#main-content h1').inner_text()
        RESULTS[-1]['offlinePageErrors']=errors
        context.close()
    browser.close()
(ROOT/'gallery-capacity-v45-ui-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(RESULTS,ensure_ascii=False,indent=2))
