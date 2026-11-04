from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
SCRIPT_DIR=Path(__file__).resolve().parent; ROOT=SCRIPT_DIR.parents[1]; QA=SCRIPT_DIR/'visual-redesign'; QA.mkdir(parents=True,exist_ok=True); results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',args=['--disable-extensions'])
 for width,height,label in [(1440,1000,'desktop'),(390,844,'mobile')]:
  context=browser.new_context(viewport={'width':width,'height':height},is_mobile=width<500,has_touch=width<500);page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  response=page.goto('http://127.0.0.1:8766/',wait_until='networkidle',timeout=30000);page.locator('.project-card').first.wait_for(state='visible',timeout=10000)
  for view in ['projects','showcase','settings']:
   page.locator(f'[data-view="{view}"]:visible').first.click();page.wait_for_timeout(100)
   if view=='projects':
    images=page.locator('.project-card img');loaded=[]
    for i in range(images.count()):
     image=images.nth(i);image.scroll_into_view_if_needed();image.evaluate('e=>e.decode()');loaded.append(image.get_attribute('src'))
   else: loaded=[]
   dims=page.evaluate('''() => ({width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,active:[...document.querySelectorAll('[data-view][aria-current="page"]')].map(x=>x.dataset.view)})''')
   filename=f'folio-v60-{label}-{view}.png';page.screenshot(path=str(QA/filename),full_page=True,animations='disabled')
   results.append({'viewport':label,'view':view,'http':response.status if response else None,**dims,'coverSources':loaded,'errors':errors.copy(),'screenshot':filename})
  context.close()
 browser.close()
(QA/'folio-v60-navigation-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(results,ensure_ascii=True,indent=2))