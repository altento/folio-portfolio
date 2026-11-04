from __future__ import annotations
import asyncio, json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

OUT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8766/'

JS=r'''(selector) => {
 const el=document.querySelector(selector); if(!el) return {selector,found:false};
 const style=getComputedStyle(el);
 const parse=v=>{const m=v.match(/rgba?\(([^)]+)\)/);if(!m)return null;const a=m[1].split(',').map(x=>parseFloat(x.trim()));return {r:a[0],g:a[1],b:a[2],a:a[3]??1}};
 const bgChain=[];let cur=el,solid=null;
 while(cur&&cur!==document.documentElement){const cs=getComputedStyle(cur);const bg=parse(cs.backgroundColor);bgChain.push({node:cur.tagName.toLowerCase()+(cur.id?'#'+cur.id:''),backgroundColor:cs.backgroundColor,backgroundImage:cs.backgroundImage});if(bg&&bg.a>=.99){solid={node:cur.tagName.toLowerCase()+(cur.id?'#'+cur.id:''),color:bg};break}cur=cur.parentElement}
 const rect=el.getBoundingClientRect();
 return {selector,found:true,text:(el.innerText||el.textContent||'').trim(),theme:document.documentElement.dataset.theme||'light',foreground:style.color,foreground_color:parse(style.color),own_background:style.backgroundColor,own_background_color:parse(style.backgroundColor),backgroundImage:style.backgroundImage,nearest_solid_background:solid,background_chain:bgChain.slice(0,5),opacity:style.opacity,fontSize:style.fontSize,fontWeight:style.fontWeight,visible:rect.width>0&&rect.height>0&&style.visibility!=='hidden'&&style.display!=='none',disabled:!!el.matches(':disabled,[aria-disabled="true"]')};
}'''

def luminance(c):
 def f(v):
  v=v/255
  return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 return .2126*f(c['r'])+.7152*f(c['g'])+.0722*f(c['b'])
def ratio(a,b):
 l1,l2=sorted((luminance(a),luminance(b)),reverse=True);return round((l1+.05)/(l2+.05),2)

async def main():
 scans=[];errors=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(channel='chrome',headless=True)
  # A fresh ephemeral context: no user Chrome profile, and service workers disabled.
  context=await browser.new_context(viewport={'width':1440,'height':1100},service_workers='block',color_scheme='light')
  page=await context.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
  response=await page.goto(URL,wait_until='networkidle',timeout=45000)
  if not response or response.status!=200:raise RuntimeError(f'Local app unavailable at {URL}: {response.status if response else "no response"}')
  await page.wait_for_selector('#main-content:not([aria-busy="true"])',timeout=15000)
  await page.wait_for_timeout(300)
  for theme in ('light','dark'):
   actual=await page.locator('html').get_attribute('data-theme') or 'light'
   if actual!=theme:
    await page.locator('#theme-toggle').click();await page.wait_for_timeout(150)
   await page.locator('[data-view="projects"]:visible').first.click();await page.wait_for_timeout(200)
   hint=await page.evaluate(JS,'#search-input ~ kbd')
   scans.append({'theme':theme,'state':'projects_search_hint','target':hint})
   # Open a read-only case detail in the same isolated context.
   first=page.locator('[data-detail]:visible').first
   if not await first.count(): raise RuntimeError('No demo project is available for detail-dialog contrast check')
   await first.click();await page.locator('#detail-dialog[open]').wait_for()
   close=await page.evaluate(JS,'#detail-dialog .detail-close')
   scans.append({'theme':theme,'state':'project_detail_close','target':close})
   await page.keyboard.press('Escape');await page.wait_for_timeout(100)
  await browser.close()

 results=[]
 for scan in scans:
  t=scan['target']; fg=t.get('foreground_color'); bg=t.get('nearest_solid_background',{}).get('color')
  if fg and bg:
   # For opaque own backgrounds use those directly; otherwise use nearest solid ancestor.
   base=t.get('own_background_color')
   if not base or base['a']<.99:base=bg
   value=ratio(fg,base);scan['contrast_ratio']=value
   target=3 if scan['state']=='project_detail_close' else 4.5
   scan['required_ratio']=target;scan['result']='PASS' if value>=target else 'FAIL'
  else:scan['contrast_ratio']=None;scan['result']='REVIEW'
 report={'audit':'Targeted contrast regression, v97','source':URL,'captured_at_utc':datetime.now(timezone.utc).isoformat(),'browser':'Chromium via Playwright; isolated new context; service workers blocked','scope':'Only projects search shortcut hint and project-detail close glyph, light/dark themes.','database_safety':'No user browser profile used. Local app may seed demo content into ephemeral IndexedDB only. No imports, user data, edits, or form submissions.','method':'Computed foreground and nearest opaque solid CSS background; WCAG luminance contrast formula. Image/gradient backgrounds are reported but not pixel sampled.','page_errors':errors,'scans':scans}
 (OUT/'contrast-v97-targeted-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# Целевой контрастный прогон v97','','- URL: `'+URL+'`','- Область: только shortcut-hint поиска и крестик закрытия detail dialog в обеих темах.','- Профиль: изолированный Chrome context, service workers отключены; пользовательская база не открывалась.','','| Тема | Элемент | Цвет текста | Solid-фон | Контраст | Порог | Итог |','|---|---|---|---|---:|---:|---|']
 for s in scans:
  t=s['target'];fg=t.get('foreground_color');bg=t.get('own_background_color') or (t.get('nearest_solid_background') or {}).get('color',{});rgb=lambda c:'#%02x%02x%02x'%(round(c['r']),round(c['g']),round(c['b'])) if c else 'не определён'
  lines.append(f"| {s['theme']} | {s['state']} | {rgb(t.get('foreground_color'))} | {rgb(bg)} | {s.get('contrast_ratio','—')} | {s.get('required_ratio','—')} | {s['result']} |")
 lines+=['','Исходные computed styles и цепочка фона: `contrast-v97-targeted-results.json`.','']
 (OUT/'contrast-v97-targeted-report.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps({'results':[(s['theme'],s['state'],s['contrast_ratio'],s['required_ratio'],s['result']) for s in scans],'errors':errors,'json':str(OUT/'contrast-v97-targeted-results.json'),'markdown':str(OUT/'contrast-v97-targeted-report.md')},ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(main())

