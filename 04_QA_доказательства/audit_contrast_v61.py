from pathlib import Path
import json
from playwright.sync_api import sync_playwright

QA = Path(__file__).resolve().parent / 'contrast-v61'
QA.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:8766/'

def rgb(hex_color):
    if hex_color.startswith('rgb'):
        import re
        return tuple(int(x) for x in re.findall(r'\d+',hex_color)[:3])
    value=hex_color.lstrip('#')
    return tuple(int(value[i:i+2],16) for i in (0,2,4))
def luminance(color):
    channels=[v/255 for v in color]
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return .2126*linear[0]+.7152*linear[1]+.0722*linear[2]
def ratio(fg,bg):
    a,b=sorted((luminance(rgb(fg)),luminance(rgb(bg))),reverse=True)
    return (a+.05)/(b+.05)

results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', args=['--disable-extensions'])
    for width,height,label in [(1920,1080,'desktop'),(390,844,'mobile-390'),(320,568,'mobile-320')]:
        context=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<500,has_touch=width<500,service_workers='block')
        page=context.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        response=page.goto(URL,wait_until='networkidle',timeout=30000)
        page.locator('.project-card').first.wait_for(state='visible',timeout=12000)
        routes=['dashboard','projects','showcase','settings']
        for route in routes:
            if route!='dashboard':
                page.locator(f'[data-view="{route}"]:visible').first.click()
                page.wait_for_timeout(80)
            dims=page.evaluate('''() => ({width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,active:[...document.querySelectorAll('[data-view][aria-current="page"]')].map(x=>x.dataset.view)})''')
            for theme in ['light','dark']:
                if (page.locator('html').get_attribute('data-theme') or 'light') != theme:
                    page.locator('#theme-toggle').click()
                contrast=page.evaluate('''() => {
                  const c=s=>getComputedStyle(document.querySelector(s)).color;
                  const v=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
                  return {muted:v('--muted'),sidebarLabel:c('.sidebar .workspace-label'),sidebarItem:c('.sidebar .nav-item'),mobileIdle:c('.mobile-nav-item'),mobileActive:c('.mobile-nav-item.active'),mobileActiveText:c('.mobile-nav-item.active small')};
                }''')
                bg='#202126' if theme=='dark' else '#f5f5f3'
                checks={
                    'muted-on-canvas':ratio(contrast['muted'],bg),
                    'sidebar-label':ratio(contrast['sidebarLabel'],'#202126'),
                    'sidebar-nav':ratio(contrast['sidebarItem'],'#202126'),
                    'mobile-nav-idle':ratio(contrast['mobileIdle'],'#202126' if theme=='dark' else '#ffffff'),
                    'mobile-nav-active':ratio(contrast['mobileActive'],'#202126' if theme=='dark' else '#ffffff'),
                    'mobile-nav-active-label':ratio(contrast['mobileActiveText'],'#202126' if theme=='dark' else '#ffffff'),
                }
                image_status=page.locator('img').evaluate_all('''async els => Promise.all(els.map(async e => {e.loading='eager';try{await e.decode();return {src:e.currentSrc||e.src,ok:e.naturalWidth>0,width:e.naturalWidth}}catch{return {src:e.currentSrc||e.src,ok:false,width:e.naturalWidth}}}))''')
                filename=f'folio-v61-{label}-{route}-{theme}.png'
                page.screenshot(path=str(QA/filename),full_page=True,animations='disabled')
                failed={k:v for k,v in checks.items() if v<4.5}
                bad_images=[image for image in image_status if not image['ok']]
                results.append({'viewport':label,'route':route,'theme':theme,'http':response.status if response else None,**dims,'contrast':checks,'failedContrast':failed,'images':image_status,'brokenImages':bad_images,'errors':errors.copy(),'screenshot':filename})
        context.close()
    browser.close()
(QA/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'screens':len(results),'failures':[r for r in results if r['overflow'] or r['failedContrast'] or r['brokenImages'] or r['errors'] or r['http']!=200],'allClear':all(not(r['overflow'] or r['failedContrast'] or r['brokenImages'] or r['errors'] or r['http']!=200) for r in results),'output':str(QA)},ensure_ascii=True,indent=2))
