import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/Windows-10/AppData/Local/npm-cache/_npx/9833c18b2d85bc59/node_modules/playwright');
const base='http://127.0.0.1:8766/';
const out='C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_01-11-2026';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--no-first-run','--no-default-browser-check']});
const result={date:'2026-11-01',version:'folio-shell-v62-atomic-portfolio-writes',errors:[],externalRequests:[],views:[],screens:[]};
try {
 const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'allow'});
 const page=await context.newPage();
 page.on('pageerror',e=>result.errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')result.errors.push(m.text())});
 page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))result.externalRequests.push(r.url())});
 await page.goto(base,{waitUntil:'networkidle',timeout:20000});
 result.scriptHosts=await page.locator('script[src]').evaluateAll(xs=>xs.map(x=>new URL(x.src).hostname));
 const routes=['dashboard','projects','showcase','settings'];
 for(const [width,height] of [[1440,900],[390,844],[320,568]]){
  await page.setViewportSize({width,height});
  for(const route of routes){
   const selector=width<821?`.mobile-nav [data-view="${route}"]`:`.sidebar .nav-item[data-view="${route}"]`;
   await page.locator(selector).click(); await page.waitForTimeout(80);
   const m=await page.evaluate(()=>{
    const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0};
    const controls=[...document.querySelectorAll('button,a[href],input:not([type=file]),select,textarea,[role=button]')].filter(visible);
    const name=e=>{const a=e.getAttribute('aria-label');if(a)return a;const ids=e.getAttribute('aria-labelledby');if(ids)return ids.split(/\s+/).map(id=>document.getElementById(id)?.innerText||'').join(' ').trim();const labels=e.labels?[...e.labels].map(x=>x.innerText.trim()).filter(Boolean):[];if(labels.length)return labels.join(' ');return(e.innerText||e.getAttribute('alt')||e.getAttribute('title')||e.getAttribute('placeholder')||'').trim()};
    const unnamed=controls.filter(e=>!name(e)).map(e=>({tag:e.tagName,type:e.type||'',role:e.getAttribute('role'),html:e.outerHTML.slice(0,160)}));
    const unlabeled=[...document.querySelectorAll('input:not([type=hidden]):not([type=file]),select,textarea')].filter(visible).filter(e=>!(e.labels?.length||e.getAttribute('aria-label')||e.getAttribute('aria-labelledby'))).map(e=>({tag:e.tagName,type:e.type||'',name:e.name||'',id:e.id}));
    const targets=controls.map(e=>{let t=e;if((e.type==='checkbox'||e.type==='radio')&&e.labels?.[0])t=e.labels[0];const r=t.getBoundingClientRect();return{name:name(e).slice(0,70),w:Math.round(r.width),h:Math.round(r.height),tag:e.tagName,inline:e.tagName==='A'&&!e.classList.contains('button')}});
    const imgs=[...document.images].filter(visible).map(i=>({alt:i.getAttribute('alt'),loaded:i.complete&&i.naturalWidth>0,src:i.getAttribute('src')}));
    return{controlCount:targets.length,smallestTarget:targets.length?Math.min(...targets.flatMap(t=>[t.w,t.h])):0,viewport:{width:innerWidth,height:innerHeight},document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},h1:[...document.querySelectorAll('h1')].filter(visible).length,landmarks:{main:document.querySelectorAll('main').length,nav:document.querySelectorAll('nav').length},unnamed,unlabeled,smallTargets:targets.filter(t=>(t.w<24||t.h<24)&&!t.inline),targetsUnder44:targets.filter(t=>(t.w<44||t.h<44)&&!t.inline),imagesMissingAlt:imgs.filter(i=>i.alt===null),imagesNotLoaded:imgs.filter(i=>!i.loaded),imageCount:imgs.length};
   });
   const entry={width,height,route,...m};
   if(m.document.width!==width)throw new Error(`overflow: ${JSON.stringify(entry)}`);
   if(m.unnamed.length||m.unlabeled.length)throw new Error(`unnamed controls: ${JSON.stringify(entry)}`);
   if(m.smallTargets.length||(width<821&&m.targetsUnder44.length))throw new Error(`small tap target: ${JSON.stringify(entry)}`);
   if(m.imagesMissingAlt.length||m.imagesNotLoaded.length)throw new Error(`image accessibility/load: ${JSON.stringify(entry)}`);
   if(m.h1!==1||m.landmarks.main<1)throw new Error(`heading/landmark: ${JSON.stringify(entry)}`);
   result.views.push(entry);
   const shot=`web-a11y-v62-${route}-${width}x${height}.png`;
   await page.screenshot({path:`${out}/${shot}`}); result.screens.push(shot);
  }
  const projects=width<821?'.mobile-nav [data-view="projects"]':'.sidebar .nav-item[data-view="projects"]';
  await page.locator(projects).click();
  await page.locator('[data-detail]').first().click(); await page.locator('#detail-dialog[open]').waitFor();
  const detail=await page.evaluate(()=>({dialogOpen:document.querySelector('#detail-dialog').open,ariaLabelledby:document.querySelector('#detail-dialog').getAttribute('aria-labelledby'),titleId:!!document.querySelector('#detail-title'),closeName:document.querySelector('#detail-dialog [data-close-dialog]')?.getAttribute('aria-label'),documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth}));
  if(!detail.dialogOpen||!detail.ariaLabelledby||!detail.titleId||!detail.closeName||detail.documentWidth!==width)throw new Error(`detail dialog invalid at ${width}: ${JSON.stringify(detail)}`);
  result.details??=[]; result.details.push({width,...detail});
  const detailShot=`web-a11y-v62-detail-${width}x${height}.png`; await page.screenshot({path:`${out}/${detailShot}`});result.screens.push(detailShot);
  await page.keyboard.press('Escape'); await page.locator('#detail-dialog').waitFor({state:'hidden'});
  await page.locator('[data-action="new-project"]:visible').first().click(); await page.locator('#project-dialog[open]').waitFor();
  const form=await page.evaluate(()=>({dialogOpen:document.querySelector('#project-dialog').open,documentWidth:document.documentElement.scrollWidth,viewportWidth:innerWidth,activeName:document.activeElement?.name||document.activeElement?.id||document.activeElement?.tagName,actions:[...document.querySelectorAll('#project-dialog .dialog-actions button')].map(b=>{let r=b.getBoundingClientRect();return{label:b.innerText.trim(),w:Math.round(r.width),h:Math.round(r.height),visible:r.top>=0&&r.bottom<=innerHeight}}),unlabeled:[...document.querySelectorAll('#project-dialog input:not([type=hidden]),#project-dialog select,#project-dialog textarea')].filter(e=>e.offsetWidth&&!(e.labels?.length||e.getAttribute('aria-label')||e.getAttribute('aria-labelledby'))).map(e=>e.name||e.id)}));
  if(!form.dialogOpen||form.documentWidth!==width||form.unlabeled.length)throw new Error(`form invalid at ${width}: ${JSON.stringify(form)}`);
  form.headingVisibleAtOpen=await page.evaluate(()=>{const r=document.querySelector('#project-dialog .dialog-head').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight});
  if(!form.headingVisibleAtOpen)throw new Error(`form heading not visible at ${width}`);
  if(width===320){const shot=`web-a11y-v62-form-start-${width}x${height}.png`;await page.screenshot({path:`${out}/${shot}`});result.screens.push(shot)}
  await page.locator('#project-dialog .dialog-actions button').last().scrollIntoViewIfNeeded();
  form.actionsAfterScroll=await page.evaluate(()=>[...document.querySelectorAll('#project-dialog .dialog-actions button')].map(b=>{const r=b.getBoundingClientRect();return{label:b.innerText.trim(),w:Math.round(r.width),h:Math.round(r.height),visible:r.top>=0&&r.bottom<=innerHeight}}));
  if(!form.actionsAfterScroll.every(x=>x.visible))throw new Error(`form actions unreachable at ${width}: ${JSON.stringify(form)}`);
  result.forms??=[];result.forms.push({width,...form});
  const formShot=`web-a11y-v62-form-${width}x${height}.png`;await page.screenshot({path:`${out}/${formShot}`});result.screens.push(formShot);
  await page.keyboard.press('Escape');await page.locator('#project-dialog').waitFor({state:'hidden'});
 }
 await page.emulateMedia({reducedMotion:'reduce'}); result.reducedMotion=await page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches");
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.locator('#theme-toggle').click();result.darkTheme=await page.evaluate('document.documentElement.dataset.theme');
 await page.locator('#theme-toggle').click();result.lightThemeRestored=await page.evaluate('document.documentElement.dataset.theme');
 if(!result.reducedMotion||result.darkTheme!=='dark'||result.lightThemeRestored!=='light')throw new Error('reduced motion/theme verification failed');
 await context.close();
} finally {await browser.close()}
await fs.writeFile(`${out}/web-accessibility-audit-v62-2026-11-01.json`,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({views:result.views.length,details:result.details,forms:result.forms,errors:result.errors,externalRequests:result.externalRequests,scriptHosts:result.scriptHosts,reducedMotion:result.reducedMotion,themes:[result.darkTheme,result.lightThemeRestored],screens:result.screens.length},null,2));

