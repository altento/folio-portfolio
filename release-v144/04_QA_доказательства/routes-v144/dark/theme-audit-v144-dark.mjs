import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const out=process.env.FOLIO_QA_DIR;
const axe=await readFile(process.env.FOLIO_AXE_PATH,'utf8');
const port=process.env.FOLIO_PORT;
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const routes=[['dashboard','Ваши проекты'],['projects','Все проекты'],['showcase','Работы'],['settings','Настройки и данные']];
const errors=[],badResponses=[],imageErrors=[],states={};

async function prepare(ctx){
  await ctx.addInitScript(()=>localStorage.setItem('folio-theme','dark'));
  const p=await ctx.newPage();
  p.on('pageerror',e=>errors.push(String(e)));
  p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  p.on('response',r=>{if(r.status()>=400)badResponses.push({status:r.status(),url:r.url()})});
  const res=await p.goto(`http://127.0.0.1:${port}/?folio-desktop=1`,{waitUntil:'networkidle'});
  if(!res||!res.ok())throw new Error(`HTTP ${res?.status()}`);
  await p.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
  await p.addScriptTag({content:axe});
  return p;
}

async function inspect(p,route,label,key,file){
  await p.locator(`[data-view="${route}"]:visible`).first().click();
  await p.waitForTimeout(120);
  const row=await p.evaluate(async()=>{
    const e=document.querySelector('#page-title')||document.querySelector('main h1')||document.querySelector('h1');
    const result=await axe.run('body');
    const imgs=[...document.images];
    for(const img of imgs)if(img.getAttribute('src'))img.loading='eager';
    await Promise.all(imgs.map(img=>img.decode().catch(()=>{})));
    return {
      theme:document.documentElement.dataset.theme,
      title:e?.innerText||'',
      viewport:innerWidth,
      scroll:document.documentElement.scrollWidth,
      body:document.body.scrollWidth,
      violations:result.violations.map(x=>({id:x.id,impact:x.impact,count:x.nodes.length,targets:x.nodes.slice(0,5).map(n=>n.target)})),
      incomplete:result.incomplete.map(x=>x.id),
      failedImages:imgs.filter(img=>img.getAttribute('src')&&(!img.complete||img.naturalWidth===0)).map(img=>img.currentSrc||img.src)
    };
  });
  row.title=row.title.trim();
  row.labelMatches=row.title.toLowerCase().includes(label.toLowerCase().split(' ')[0]);
  imageErrors.push(...row.failedImages);
  await p.screenshot({path:`${out}/${file}.png`,fullPage:true});
  states[key]=row;
}

const desktop=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
const d=await prepare(desktop);
for(const [route,label] of routes)await inspect(d,route,label,`desktop-${route}`,`dark-desktop-${route}-1440`);
const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
const m=await prepare(mobile);
for(const width of [390,320]){
  await m.setViewportSize({width,height:844});
  for(const [route,label] of routes)await inspect(m,route,label,`phone-${width}-${route}`,`dark-phone-${width}-${route}`);
}
const all=Object.values(states);
const summary={count:all.length,allDark:all.every(x=>x.theme==='dark'),allHeadings:all.every(x=>x.title.length>0&&x.labelMatches),allLayoutsFit:all.every(x=>x.scroll<=x.viewport&&x.body<=x.viewport),allAxeClean:all.every(x=>x.violations.length===0),allImagesLoaded:imageErrors.length===0,noRuntimeErrors:errors.length===0&&badResponses.length===0};
const result={date:'2026-11-05',build:'packaged Windows WebView2 v144; dark palette',axe:'4.14.0',states,summary,errors,badResponses,imageErrors,passed:summary.count===12&&Object.values(summary).every(x=>x===true||x===12)};
await writeFile(`${out}/theme-audit-v144-dark-results.json`,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({passed:result.passed,summary,violations:Object.fromEntries(Object.entries(states).filter(([,v])=>v.violations.length).map(([k,v])=>[k,v.violations])),imageErrors,errors,badResponses},null,2));
await browser.close();
if(!result.passed)process.exitCode=1;

