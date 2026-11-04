from __future__ import annotations
import asyncio,json,shutil,tempfile,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
QA=Path(__file__).resolve().parent;WEB=QA.parent/'02_Приложение'/'web';TEMP=Path(tempfile.mkdtemp(prefix='folio-v58-dashboard-'));SITE=TEMP/'site';CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
 def log_message(self,*_args):pass
async def main():
 shutil.copytree(WEB,SITE);server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)));threading.Thread(target=server.serve_forever,daemon=True).start();result={'version':'v58-dashboard-insights-plus-generated-hero','checks':{},'errors':[]}
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check']);context=await browser.new_context(viewport={'width':1440,'height':900},service_workers='allow');page=await context.new_page()
   page.on('pageerror',lambda error:result['errors'].append(str(error)));page.on('console',lambda msg:result['errors'].append(msg.text) if msg.type=='error' else None)
   response=await page.goto(f'http://127.0.0.1:{server.server_port}/#dashboard',wait_until='networkidle',timeout=20000);assert response and response.status==200
   await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v58-illustrated-dashboard-hero')",timeout=15000)
   await page.locator('.portfolio-insights').wait_for(state='visible')
   result['checks']['insightsUseExistingCaseStoryChecklist']=await page.locator('.insight-list').inner_text() and 'задачу и контекст' in (await page.locator('.insight-list').inner_text()).lower()
   insight_text=await page.locator('.portfolio-insights').inner_text();result['checks']['noQualityScoreOrRanking']=not any(token in insight_text.lower() for token in ('балл из 100','рейтинг качества','оценка:'))
   status_labels=await page.locator('.status-row').evaluate_all('(rows)=>rows.map(row=>row.getAttribute("aria-label"))');result['checks']['statusDistributionReflectsThreeDemoCases']=len(status_labels)==4 and any('В разработке: 1 ' in label for label in status_labels) and any('Завершён: 1 ' in label for label in status_labels) and any('Опубликован: 1 ' in label for label in status_labels)
   result['checks']['topTechnologiesShowProjectFrequency']=await page.locator('.insight-technologies li').count()>0 and 'JavaScript' in (await page.locator('.insight-technologies').inner_text())
   result['checks']['suggestionExplainsOptionality']= 'добровольные идеи' in (await page.locator('.insight-intro').inner_text()).lower() and 'без оценки качества' in (await page.locator('.insight-card').first.inner_text()).lower()
   result['checks']['suggestionRussianCopyIsNatural']='Опишите задачу и контекст' in await page.locator('.insight-list').inner_text()
   await page.locator('.cover-image').evaluate_all("imgs=>imgs.forEach(img=>img.loading='eager')");await page.locator('.recent-grid').scroll_into_view_if_needed();await page.locator('.recent-grid').screenshot(path=str(QA/'web-dashboard-insights-v58-recent-cases-1440x900.png'));await page.wait_for_function("[...document.querySelectorAll('.cover-image')].every(img=>img.complete&&img.naturalWidth>0)",timeout=10000);await page.evaluate('window.scrollTo(0,0)')
   result['diagnostics']={'coverImages':await page.locator('.cover-image').evaluate_all("imgs=>imgs.map(img=>({src:img.getAttribute('src'),loaded:img.complete,width:img.naturalWidth,opacity:getComputedStyle(img).opacity,display:getComputedStyle(img).display}))")}
   contrast_script="""()=>{const l=c=>{const v=c.match(/[0-9.]+/g).slice(0,3).map(Number).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2]},r=(a,b)=>{const x=l(a),y=l(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)},q=(selector,bgSelector)=>{const a=document.querySelector(selector),b=document.querySelector(bgSelector);return r(getComputedStyle(a).color,getComputedStyle(b).backgroundColor)};return {bodyText:q('.status-row>span','.insight-mix'),countPill:q('.insight-count','.insight-count'),stepNumber:q('.insight-number','.insight-number')}}"""
   light_contrast=await page.evaluate(contrast_script);result['checks']['insightLightThemeContrastAA']=min(light_contrast.values())>=4.5
   await page.locator('#theme-toggle').click();dark_contrast=await page.evaluate(contrast_script);result['checks']['insightDarkThemeContrastAA']=min(dark_contrast.values())>=4.5;result['diagnostics']={'lightContrast':light_contrast,'darkContrast':dark_contrast}
   await page.locator('#theme-toggle').click()
   await page.screenshot(path=str(QA/'web-dashboard-insights-v58-desktop-1440x900.png'),full_page=False)
   await page.locator('.recent-grid').screenshot(path=str(QA/'web-dashboard-insights-v58-recent-cards-1440x900.png'))
   await page.locator('[data-insight-edit="2"]').click();await page.locator('#project-dialog').wait_for(state='visible')
   result['checks']['insightOpensTheRelevantCase']=await page.locator('#project-form [name="title"]').input_value()=='CRM для клининговой компании'
   result['checks']['dashboardAndEditorChecklistStayInSync']=await page.locator('#case-guide-count').inner_text()=='3 из 6' and 'Задача и контекст' in await page.locator('#case-guide-next').inner_text()
   await page.locator('#project-form [name="context"]').fill('Заказчику было сложно отслеживать распределение заказов между бригадами.')
   result['checks']['editingAFieldUpdatesSharedChecklist']=await page.locator('#case-guide-count').inner_text()=='4 из 6'
   await page.keyboard.press('Escape');await page.locator('#project-dialog').wait_for(state='hidden')
   result['checks']['closingSuggestionEditorKeepsDashboardStable']=await page.locator('.portfolio-insights').is_visible() and 'CRM для клининговой компании' in await page.locator('.insight-list').inner_text()
   await page.wait_for_timeout(500)
   await page.evaluate("""()=>new Promise((resolve,reject)=>{const request=indexedDB.open('folio-workspace',1);request.onsuccess=()=>{const transaction=request.result.transaction('records','readwrite');transaction.objectStore('records').delete('project-draft');transaction.oncomplete=()=>resolve(true);transaction.onerror=()=>reject(transaction.error)};request.onerror=()=>reject(request.error)})""")
   result['checks']['temporaryUnsavedDraftClearedOnlyInQAPage']=await page.evaluate("""()=>new Promise((resolve,reject)=>{const request=indexedDB.open('folio-workspace',1);request.onsuccess=()=>{const get=request.result.transaction('records','readonly').objectStore('records').get('project-draft');get.onsuccess=()=>resolve(get.result?.value==null);get.onerror=()=>reject(get.error)};request.onerror=()=>reject(request.error)})""")
   await page.locator('#toast-region .toast').wait_for(state='hidden',timeout=5000)
   await page.set_viewport_size({'width':390,'height':844});result['checks']['mobile390NoHorizontalOverflow']=await page.evaluate('document.documentElement.scrollWidth===innerWidth')
   rect390=await page.locator('.portfolio-insights').evaluate('e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,scroll:e.scrollWidth,client:e.clientWidth}}');result['checks']['insightsFit390']=rect390['left']>=0 and rect390['right']<=390 and rect390['scroll']<=rect390['client']
   await page.locator('.portfolio-insights').scroll_into_view_if_needed();await page.evaluate("()=>{const top=document.querySelector('.portfolio-insights').getBoundingClientRect().top;window.scrollBy(0,top-70)}");await page.screenshot(path=str(QA/'web-dashboard-insights-v58-mobile-390x844.png'),full_page=False)
   await page.set_viewport_size({'width':320,'height':568});result['checks']['mobile320NoHorizontalOverflow']=await page.evaluate('document.documentElement.scrollWidth===innerWidth')
   rect320=await page.locator('.portfolio-insights').evaluate('e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,scroll:e.scrollWidth,client:e.clientWidth}}');result['checks']['insightsFit320']=rect320['left']>=0 and rect320['right']<=320 and rect320['scroll']<=rect320['client']
   await page.locator('.portfolio-insights').scroll_into_view_if_needed();await page.evaluate("()=>{const top=document.querySelector('.portfolio-insights').getBoundingClientRect().top;window.scrollBy(0,top-70)}");await page.screenshot(path=str(QA/'web-dashboard-insights-v58-mobile-320x568.png'),full_page=False)
   await page.set_viewport_size({'width':1440,'height':900})
   async def accept(dialog):await dialog.accept()
   page.once('dialog',accept);await page.locator('[data-action="clear-demo"]').click();await page.locator('.insight-list').get_by_text('Создайте первый кейс').wait_for(timeout=5000)
   result['checks']['emptyLibraryOffersFirstStep']=await page.locator('.insight-list').get_by_text('Создайте первый кейс').count()==1
   status_summary=await page.locator('.status-distribution').inner_text();result['checks']['emptyLibraryStatusChartIsHonest']=status_summary.count('0')==4
   await page.locator('.insight-list [data-action="new-project"]').click();await page.locator('#project-dialog').wait_for(state='visible');result['checks']['emptyStateActionOpensNewCase']=await page.locator('#project-form [name="title"]').input_value()=='';await page.keyboard.press('Escape')
   await page.set_viewport_size({'width':1440,'height':900});result['checks']['serviceWorkerUsesV58']=await page.evaluate("async()=>{const keys=await caches.keys();return keys.includes('folio-shell-v58-illustrated-dashboard-hero')&&!keys.some(k=>k==='folio-shell-v54-bulk-actions')}")
   assert all(result['checks'].values()),{'checks':result['checks'],'390':rect390,'320':rect320};assert not result['errors'],result['errors'];await browser.close()
 finally:server.shutdown();server.server_close()
 (QA/'web-dashboard-insights-v58-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
