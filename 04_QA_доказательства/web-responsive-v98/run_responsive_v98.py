import asyncio, json, os, time
from pathlib import Path
from playwright.async_api import async_playwright

BASE = 'http://127.0.0.1:8767/'
OUT = Path(__file__).resolve().parent
VIEWPORTS = [(320,568),(390,844),(768,900),(820,900),(821,900),(1024,768),(1440,900)]
SECTIONS = ['dashboard','projects','settings']
ERRORS=[]
RESULTS=[]

def name(w,h,section,suffix=''):
    return f'v98-{section}-{w}x{h}{suffix}.png'

async def metrics(page, w, h, section, state='page'):
    return await page.evaluate('''({w,h,section,state}) => {
      const r = e => { if(!e) return null; const x=e.getBoundingClientRect(); return {x:Math.round(x.x),y:Math.round(x.y),width:Math.round(x.width),height:Math.round(x.height),right:Math.round(x.right),bottom:Math.round(x.bottom)}; };
      const main=document.querySelector('#main-content'), nav=document.querySelector('.mobile-nav'), side=document.querySelector('.sidebar'), top=document.querySelector('.topbar'), dlg=document.querySelector('dialog[open]');
      const vw=document.documentElement.clientWidth, docw=document.documentElement.scrollWidth;
      const offenders=[...document.querySelectorAll('body *')].filter(e=>{const s=getComputedStyle(e); if(s.position==='fixed'||s.position==='absolute'||s.display==='none'||s.visibility==='hidden') return false; const b=e.getBoundingClientRect(); return b.width>0&&(b.left < -1 || b.right > vw+1);}).slice(0,12).map(e=>({tag:e.tagName,cls:typeof e.className==='string'?e.className:'',text:(e.innerText||'').trim().slice(0,45),left:Math.round(e.getBoundingClientRect().left),right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width)}));
      const mainBottom=main?.getBoundingClientRect().bottom??0, navTop=nav?.getBoundingClientRect().top??Infinity, lastContent=main?.lastElementChild;
      const dlgActions=dlg?.querySelector('.dialog-actions'), form=dlg?.querySelector('.dialog-form'), selectVisible=document.querySelector('.select-visible-control');
      return {width:w,height:h,section,state,documentClientWidth:vw,documentScrollWidth:docw,horizontalOverflow:docw>vw+1,main:r(main),topbar:r(top),mobileNav:r(nav),sidebar:r(side),dialog:r(dlg),dialogScroll:dlg?{clientWidth:dlg.clientWidth,scrollWidth:dlg.scrollWidth,clientHeight:dlg.clientHeight,scrollHeight:dlg.scrollHeight,scrollTop:dlg.scrollTop,form:form?{rect:r(form),clientHeight:form.clientHeight,scrollHeight:form.scrollHeight,scrollTop:form.scrollTop}:null,actions:r(dlgActions)}:null,selectVisible:r(selectVisible),selectVisibleFullyAboveBottomNav:!!selectVisible&&selectVisible.getBoundingClientRect().bottom<=navTop,lastContent:r(lastContent),navVisible:!!nav&&getComputedStyle(nav).display!=='none',sidebarVisible:!!side&&getComputedStyle(side).display!=='none',activeNav:[...document.querySelectorAll('[data-view][aria-current="page"],.nav-item.active,.mobile-nav-item.active')].map(e=>e.dataset.view),mainBusy:main?.getAttribute('aria-busy'),bodyBottomPadding:getComputedStyle(document.querySelector('.workspace')).paddingBottom,mainMayOverlapBottomNav:!!nav&&getComputedStyle(nav).display!=='none'&&navTop<mainBottom,bottomContentCoveredByNav:!!nav&&getComputedStyle(nav).display!=='none'&&lastContent?.getBoundingClientRect().bottom>navTop+1,offenders};
    }''', {'w':w,'h':h,'section':section,'state':state})

async def main():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    context = await browser.new_context(viewport={'width':1440,'height':900}, device_scale_factor=1, is_mobile=False, has_touch=False, reduced_motion='reduce')
    page = await context.new_page()
    page.on('pageerror', lambda err: ERRORS.append({'type':'pageerror','message':str(err)}))
    page.on('console', lambda msg: ERRORS.append({'type':'console','level':msg.type,'message':msg.text}) if msg.type=='error' else None)
    page.on('requestfailed', lambda req: ERRORS.append({'type':'requestfailed','url':req.url,'failure':req.failure}))
    response = await page.goto(BASE+'#dashboard', wait_until='networkidle', timeout=30000)
    try: await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') !== 'true'", timeout=15000)
    except: pass
    await page.wait_for_timeout(500)
    startup = await page.locator('#main-content').inner_text()
    for w,h in VIEWPORTS:
      await page.set_viewport_size({'width':w,'height':h})
      for section in SECTIONS:
        selector = (f'.mobile-nav button[data-view="{section}"]' if w<=820 else f'.sidebar button[data-view="{section}"]')
        await page.locator(selector).click(timeout=5000)
        try: await page.wait_for_function("document.querySelector('#main-content')?.getAttribute('aria-busy') !== 'true'", timeout=5000)
        except: pass
        await page.wait_for_timeout(120)
        m=await metrics(page,w,h,section)
        RESULTS.append(m)
        await page.screenshot(path=str(OUT/name(w,h,section)), full_page=False, animations='disabled')
        if w<=820:
          await page.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
          await page.wait_for_timeout(100)
          bm=await metrics(page,w,h,section,'page-bottom')
          RESULTS.append(bm)
          await page.screenshot(path=str(OUT/name(w,h,section,'-bottom')), full_page=False, animations='disabled')
          await page.evaluate('window.scrollTo(0,0)')
        # Check main section has rendered and section state is navigated.
        # Test the project dialog only: open, measure, screenshot, close with Escape; no form input/save.
        if section == 'dashboard':
          trigger=page.locator('[data-action="new-project"]:visible').first
          if await trigger.count():
            try:
              await trigger.click(timeout=2000)
              await page.wait_for_timeout(120)
              dm=await metrics(page,w,h,section,'new-project-dialog')
              RESULTS.append(dm)
              await page.screenshot(path=str(OUT/name(w,h,section,'-new-project-dialog')), full_page=False, animations='disabled')
              await page.locator('#project-dialog').evaluate('(e)=>e.scrollTo(0,e.scrollHeight)')
              await page.wait_for_timeout(100)
              endm=await metrics(page,w,h,section,'new-project-dialog-bottom')
              endm['actionsVisible'] = await page.locator('#project-form .dialog-actions').is_visible()
              endm['actionsWithinViewport'] = await page.evaluate("() => {const a=document.querySelector('#project-form .dialog-actions')?.getBoundingClientRect(); return !!a&&a.top>=0&&a.bottom<=innerHeight}")
              RESULTS.append(endm)
              await page.screenshot(path=str(OUT/name(w,h,section,'-new-project-dialog-bottom')), full_page=False, animations='disabled')
              await page.keyboard.press('Escape')
              await page.wait_for_timeout(80)
              dm['closedByEscape']=not await page.locator('dialog[open]').count()
            except Exception as ex:
              RESULTS.append({'width':w,'height':h,'section':section,'state':'new-project-dialog','error':str(ex)})
    console_errors=[e for e in ERRORS if e['type'] in ('pageerror','console')]
    data={'source':BASE,'httpStatus':response.status if response else None,'startupMainText':startup[:300],'viewportMatrix':VIEWPORTS,'sections':SECTIONS,'results':RESULTS,'browserErrors':ERRORS,'summary':{'pageCount':len([x for x in RESULTS if x.get('state')=='page']),'dialogCount':len([x for x in RESULTS if x.get('state')=='new-project-dialog' and not x.get('error')]),'horizontalOverflowPages':[{k:x[k] for k in ('width','height','section','state','documentClientWidth','documentScrollWidth','offenders')} for x in RESULTS if x.get('horizontalOverflow')],'openDialogWidthHeightIssues':[{k:x[k] for k in ('width','height','dialog','offenders')} for x in RESULTS if x.get('state')=='new-project-dialog' and x.get('dialog') and (x['dialog']['x'] < -1 or x['dialog']['right'] > x['documentClientWidth']+1 or x['dialog']['bottom'] > x['height']+1)],'runtimeErrors':console_errors}}
    (OUT/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    await context.close(); await browser.close()

asyncio.run(main())


