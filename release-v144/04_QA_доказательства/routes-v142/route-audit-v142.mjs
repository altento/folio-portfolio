import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { readFile, writeFile } from 'node:fs/promises';
const out=process.env.FOLIO_QA_DIR, axe=await readFile(process.env.FOLIO_AXE_PATH,'utf8'), port=process.env.FOLIO_PORT;
const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const c=await b.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'}),p=await c.newPage();
const errors=[],badResponses=[];p.on('pageerror',e=>errors.push(String(e)));p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});p.on('response',r=>{if(r.status()>=400)badResponses.push({status:r.status(),url:r.url()})});
const goto=`http://127.0.0.1:${port}/?folio-desktop=1`;
async function settleImages(page){return await page.evaluate(async()=>{const imgs=[...document.images];for(const img of imgs)if(img.getAttribute('src'))img.loading='eager';await Promise.all(imgs.map(img=>img.decode().catch(()=>{})));return imgs.filter(img=>img.getAttribute('src')&&(!img.complete||img.naturalWidth===0)).map(img=>img.currentSrc||img.src)})}
const imageErrors=[];
const first=await p.goto(goto,{waitUntil:'networkidle'});await p.addScriptTag({content:axe});
const routes=[['dashboard','Обзор'],['projects','Мои проекты'],['showcase','Витрина'],['settings','Настройки и данные']];
const desktop={};
for(const [route,label] of routes){
 const nav=p.locator(`[data-view="${route}"]:visible`).first();await nav.click();await p.waitForTimeout(120);
 const title=(await p.evaluate(()=>{const e=document.querySelector('#page-title')||document.querySelector('main h1')||document.querySelector('h1');return e?.innerText||''})).trim();
 const overflow=await p.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
 const audit=await p.evaluate(async()=>{const r=await axe.run('body');return {violations:r.violations.map(x=>({id:x.id,impact:x.impact,count:x.nodes.length,targets:x.nodes.slice(0,4).map(n=>n.target)})),incomplete:r.incomplete.map(x=>x.id)}});
 const failedImages=await settleImages(p);imageErrors.push(...failedImages);
 await p.screenshot({path:`${out}/desktop-${route}-1440.png`,fullPage:true});
 desktop[route]={title,labelMatches:title.toLowerCase().includes(label.toLowerCase().split(' ')[0]),...overflow,axe:audit};
}
const mobile=await b.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'}),m=await mobile.newPage();
m.on('pageerror',e=>errors.push('mobile '+e));m.on('console',x=>{if(x.type()==='error')errors.push('mobile '+x.text())});m.on('response',r=>{if(r.status()>=400)badResponses.push({status:r.status(),url:r.url()})});await m.goto(goto,{waitUntil:'networkidle'});await m.addScriptTag({content:axe});
const phone={};
for(const width of [390,320]){
 await m.setViewportSize({width,height:844});phone[width]={};
 for(const [route,label] of routes){
  const nav=m.locator(`[data-view="${route}"]:visible`).first();await nav.click();await m.waitForTimeout(120);
  const title=(await m.evaluate(()=>{const e=document.querySelector('#page-title')||document.querySelector('main h1')||document.querySelector('h1');return e?.innerText||''})).trim();
  const overflow=await m.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
  const audit=await m.evaluate(async()=>{const r=await axe.run('body');return {violations:r.violations.map(x=>({id:x.id,impact:x.impact,count:x.nodes.length,targets:x.nodes.slice(0,4).map(n=>n.target)})),incomplete:r.incomplete.map(x=>x.id)}});
  const failedImages=await settleImages(m);imageErrors.push(...failedImages);
  await m.screenshot({path:`${out}/phone-${route}-${width}.png`,fullPage:true});
  phone[width][route]={title,labelMatches:title.toLowerCase().includes(label.toLowerCase().split(' ')[0]),...overflow,axe:audit};
 }
}
const result={date:'2026-11-05',build:'Windows WebView2 packaged v142',initialHttp:first.status(),routes,desktop,phone,badResponses,errors,imageErrors,allImagesLoaded:imageErrors.length===0,allLayoutsFit:Object.values(desktop).every(x=>x.scroll<=x.viewport&&x.body<=x.viewport)&&Object.values(phone).every(v=>Object.values(v).every(x=>x.scroll<=x.viewport&&x.body<=x.viewport)),allScreensHaveHeadings:[...Object.values(desktop),...Object.values(phone).flatMap(Object.values)].every(x=>x.title.length>0),noRuntimeErrors:errors.length===0&&badResponses.length===0};
result.allAxeClean=[...Object.values(desktop),...Object.values(phone).flatMap(Object.values)].every(x=>x.axe.violations.length===0);
result.allChecksPassed=first.ok()&&result.allImagesLoaded&&result.allLayoutsFit&&result.allScreensHaveHeadings&&result.noRuntimeErrors&&result.allAxeClean;
await writeFile(`${out}/route-audit-v142-results.json`,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({allChecksPassed:result.allChecksPassed,allLayoutsFit:result.allLayoutsFit,allScreensHaveHeadings:result.allScreensHaveHeadings,noRuntimeErrors:result.noRuntimeErrors,allImagesLoaded:result.allImagesLoaded,imageErrors,desktop:Object.fromEntries(Object.entries(desktop).map(([k,v])=>[k,{title:v.title,overflow:v.scroll-v.viewport,violations:v.axe.violations.length}])),phone:Object.fromEntries(Object.entries(phone).map(([w,v])=>[w,Object.fromEntries(Object.entries(v).map(([k,x])=>[k,{title:x.title,overflow:x.scroll-x.viewport,violations:x.axe.violations.length}]))])),badResponses,errors},null,2));await b.close();if(!result.allChecksPassed)process.exitCode=1;

