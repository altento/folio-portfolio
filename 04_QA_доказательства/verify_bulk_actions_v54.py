from __future__ import annotations
import asyncio, json, shutil, tempfile, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
QA=Path(__file__).resolve().parent
WEB=QA.parent/'02_Приложение'/'web'
TEMP=Path(tempfile.mkdtemp(prefix='folio-v54-bulk-'))
SITE=TEMP/'site'
CHROME=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
class Handler(SimpleHTTPRequestHandler):
    def end_headers(self): self.send_header('Cache-Control','no-store');super().end_headers()
    def log_message(self,*_args): pass
async def main():
    shutil.copytree(WEB,SITE)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    result={'version':'v54-bulk-project-actions','checks':{},'errors':[]}
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True,executable_path=str(CHROME),args=['--no-first-run','--no-default-browser-check'])
            context=await browser.new_context(viewport={'width':1440,'height':900},service_workers='allow')
            page=await context.new_page()
            page.on('pageerror',lambda error:result['errors'].append(str(error)))
            page.on('console',lambda msg:result['errors'].append(msg.text) if msg.type=='error' else None)
            response=await page.goto(f'http://127.0.0.1:{server.server_port}/#dashboard',wait_until='networkidle',timeout=20000)
            assert response and response.status==200
            await page.wait_for_function("async()=> (await caches.keys()).includes('folio-shell-v54-bulk-actions')",timeout=15000)
            await page.locator('nav [data-view="projects"]:visible').click()
            total=await page.locator('.project-card').count()
            assert total==3,total
            result['checks']['freshPortfolioHasThreeDemoProjects']=True
            result['checks']['selectionToolbarHiddenInitially']=await page.locator('.bulk-toolbar').count()==0
            await page.locator('#select-visible-projects').check()
            result['checks']['selectVisibleChoosesAll']=await page.locator('[data-select-project]:checked').count()==3 and '3 проекта выбрано' in await page.locator('.bulk-selection-count').inner_text()
            await page.screenshot(path=str(QA/'web-bulk-actions-v54-desktop-1440x900.png'),full_page=True)
            await page.locator('[data-bulk="feature"]').click()
            await page.get_by_text('Выбранные проекты добавлены в избранное.').wait_for(timeout=5000)
            result['checks']['bulkFeaturePersistsToRenderedCards']=await page.locator('.project-card .cover-kicker').count()==3 and await page.locator('.project-card .cover-kicker').all_text_contents()==['★ ИЗБРАННЫЙ КЕЙС']*3
            result['checks']['keyboardFocusMovesToNextAvailableBulkAction']=await page.evaluate('document.activeElement?.dataset?.bulk==="unfeature"')
            await page.reload(wait_until='networkidle')
            await page.locator('nav [data-view="projects"]:visible').click()
            result['checks']['bulkFeaturedStatePersistsAfterReload']=await page.locator('.project-card .cover-kicker').all_text_contents()==['★ ИЗБРАННЫЙ КЕЙС']*3
            await page.locator('#select-visible-projects').check()
            await page.locator('[data-bulk="unfeature"]').click()
            await page.get_by_text('Выбранные проекты убраны из избранного.').wait_for(timeout=5000)
            result['checks']['bulkUnfeatureWorks']=await page.locator('.project-card .cover-kicker').all_text_contents()==['КЕЙС']*3
            await page.locator('#search-input').fill('CRM')
            result['checks']['selectionSurvivesFilteringAndCountsHidden']=await page.locator('[data-select-project]:checked').count()==1 and '2 вне текущего фильтра' in await page.locator('.bulk-toolbar').inner_text()
            await page.locator('#select-visible-projects').uncheck()
            result['checks']['unselectVisibleKeepsHiddenSelection']=await page.locator('[data-select-project]:checked').count()==0 and '2 проекта выбрано' in await page.locator('.bulk-selection-count').inner_text()
            await page.locator('[data-bulk="clear"]').click()
            result['checks']['clearSelectionRemovesToolbar']=await page.locator('.bulk-toolbar').count()==0
            await page.locator('#reset-filters').click()
            cards=page.locator('.project-card')
            await cards.nth(0).locator('[data-select-project]').check()
            await cards.nth(1).locator('[data-select-project]').check()
            result['checks']['individualSelectionAndMixedVisibleState']=await page.locator('[data-select-project]:checked').count()==2 and await page.locator('#select-visible-projects').evaluate('el=>el.indeterminate')
            async def dismiss_dialog(dialog): await dialog.dismiss()
            page.once('dialog',dismiss_dialog)
            await page.locator('[data-bulk="delete"]').click()
            result['checks']['cancelDeleteLeavesProjectsAndSelectionUntouched']=await page.locator('.project-card').count()==3 and await page.locator('[data-select-project]:checked').count()==2
            async def accept_dialog(dialog): await dialog.accept()
            page.once('dialog',accept_dialog)
            await page.locator('[data-bulk="delete"]').click()
            await page.locator('.toast-action').wait_for(state='visible',timeout=5000)
            result['checks']['deleteConfirmsAndRemovesOnlySelected']=await page.locator('.project-card').count()==1 and 'Удалено 2 проекта' in await page.locator('#toast-region').inner_text()
            await page.screenshot(path=str(QA/'web-bulk-actions-v54-delete-undo-1440x900.png'))
            await page.locator('.toast-action').click()
            await page.locator('#toast-region .toast-message').get_by_text('Восстановлено проектов: 2.').wait_for(timeout=5000)
            result['checks']['undoRestoresProjectsAndOriginalSelection']=await page.locator('.project-card').count()==3 and await page.locator('[data-select-project]:checked').count()==2
            await page.locator('[data-layout-choice="list"]').click()
            result['checks']['selectionWorksInListLayout']=await page.locator('.project-list [data-select-project]:checked').count()==2
            await page.locator('#toast-region .toast').wait_for(state='hidden',timeout=5000)
            await page.set_viewport_size({'width':390,'height':844})
            result['checks']['mobile390NoHorizontalOverflow']=await page.evaluate('document.documentElement.scrollWidth===innerWidth')
            mobile=await page.locator('.bulk-toolbar').evaluate('el=>({left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,width:el.getBoundingClientRect().width,scroll:el.scrollWidth,client:el.clientWidth})')
            label390=await page.locator('.select-visible-control span').evaluate('el=>({text:el.textContent,rect:(()=>{const r=el.getBoundingClientRect();return {width:r.width,height:r.height}})(),display:getComputedStyle(el).display})')
            result['checks']['mobile390SelectionLabelVisible']=label390['rect']['width']>0 and label390['rect']['height']>0
            result['checks']['mobile390ToolbarFits']=mobile['left']>=0 and mobile['right']<=390 and mobile['scroll']<=mobile['client']
            await page.screenshot(path=str(QA/'web-bulk-actions-v54-mobile-390x844.png'),full_page=True)
            await page.set_viewport_size({'width':320,'height':568})
            result['checks']['mobile320NoHorizontalOverflow']=await page.evaluate('document.documentElement.scrollWidth===innerWidth')
            narrow=await page.locator('.bulk-toolbar').evaluate('el=>({left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,scroll:el.scrollWidth,client:el.clientWidth})')
            label320=await page.locator('.select-visible-control span').evaluate('el=>({text:el.textContent,width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height,display:getComputedStyle(el).display})')
            result['checks']['mobile320SelectionLabelVisible']=label320['width']>0 and label320['height']>0
            result['checks']['mobile320ToolbarFits']=narrow['left']>=0 and narrow['right']<=320 and narrow['scroll']<=narrow['client']
            await page.screenshot(path=str(QA/'web-bulk-actions-v54-mobile-320x568.png'),full_page=True)
            await page.set_viewport_size({'width':1440,'height':900})
            result['checks']['serviceWorkerUsesV54']=await page.evaluate("async()=>{const keys=await caches.keys();return keys.includes('folio-shell-v54-bulk-actions')&&!keys.some(k=>k==='folio-shell-v53-saved-filter-views')}")
            result['diagnostics']={'mobile390SelectionLabel':label390,'mobile320SelectionLabel':label320,'mobile390Toolbar':mobile,'mobile320Toolbar':narrow}
            assert all(result['checks'].values()),{'result':result}
            assert not result['errors'],result['errors']
            await browser.close()
    finally:
        server.shutdown();server.server_close()
    (QA/'web-bulk-actions-v54-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
