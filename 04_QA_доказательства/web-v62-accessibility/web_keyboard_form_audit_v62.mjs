import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
const require=createRequire(import.meta.url);
const {chromium}=require('C:/Users/Windows-10/AppData/Local/npm-cache/_npx/9833c18b2d85bc59/node_modules/playwright');
const base='http://127.0.0.1:8766/';
const out='C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_01-11-2026';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const results=[];
try {
 for(const [width,height] of [[1440,900],[390,844],[320,568]]){
  const page=await browser.newPage({viewport:{width,height}}); const errors=[];
  page.on('pageerror',e=>errors.push(e.message)); page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto(base,{waitUntil:'networkidle'});
  await page.keyboard.press('Tab');
  const skip=await page.evaluate(()=>{const e=document.activeElement,r=e.getBoundingClientRect();return{tag:e.tagName,className:e.className,text:(e.innerText||'').trim(),visible:r.width>0&&r.height>0&&r.top<innerHeight&&r.bottom>0}});
  if(skip.tag!=='A'||!String(skip.className).includes('skip-link')||!skip.visible)throw new Error(`Skip link not first/visible at ${width}: ${JSON.stringify(skip)}`);
  const opener=page.locator('[data-action="new-project"]:visible').first(); await page.evaluate(()=>{window.__keyboardDialogOpener=null});
  await opener.evaluate(e=>window.__keyboardDialogOpener=e); await opener.click(); await page.locator('#project-dialog[open]').waitFor();
  const first=await page.evaluate(()=>{const e=document.activeElement;return{id:e.id,name:e.name,tag:e.tagName,dialog:!!e.closest('dialog')}});
  if(first.name!=='title'||!first.dialog)throw new Error(`Focus did not start in title at ${width}: ${JSON.stringify(first)}`);
  const sequence=[]; let cycled=false;
  for(let i=0;i<60;i++){
   await page.keyboard.press('Tab');
   const f=await page.evaluate(()=>{const e=document.activeElement,r=e.getBoundingClientRect(),d=document.querySelector('#project-dialog');return{id:e.id,name:e.name,tag:e.tagName,label:(e.getAttribute('aria-label')||e.labels?.[0]?.innerText||e.innerText||e.name||e.id||e.tagName).trim().slice(0,64),inside:!!d?.contains(e),visible:r.width>0&&r.height>0&&r.top<innerHeight&&r.bottom>0,rect:{top:Math.round(r.top),bottom:Math.round(r.bottom)}}});
   sequence.push(f);
   if(!f.inside)throw new Error(`Tab escaped modal at ${width}, step ${i+1}: ${JSON.stringify(f)}`);
   if(!f.visible)throw new Error(`Focused control is outside visible viewport at ${width}, step ${i+1}: ${JSON.stringify(f)}`);
   if(sequence.length>2&&f.name==='title'){cycled=true;break;}
  }
  if(!cycled)throw new Error(`Tab order did not wrap inside the dialog at ${width}`);
  await page.keyboard.press('Escape'); await page.locator('#project-dialog').waitFor({state:'hidden'});
  const returned=await page.evaluate(()=>({isOpener:document.activeElement===window.__keyboardDialogOpener,tag:document.activeElement?.tagName,name:document.activeElement?.getAttribute('aria-label')||document.activeElement?.innerText?.trim()||document.activeElement?.id||''}));
  if(!returned.isOpener)throw new Error(`Focus did not return to dialog opener at ${width}: ${JSON.stringify(returned)}`);
  if(errors.length)throw new Error(`Browser errors at ${width}: ${errors.join(' | ')}`);
  const snap={width,height,skip,first,tabStops:sequence.length,cycled,allStopsInModal:sequence.every(x=>x.inside),allStopsVisible:sequence.every(x=>x.visible),returned,errors};
  results.push(snap); await page.screenshot({path:`${out}/web-keyboard-form-focus-${width}x${height}.png`}); await page.close();
 }
} finally {await browser.close()}
await fs.writeFile(`${out}/web-keyboard-form-focus-v62-results.json`,JSON.stringify({date:'2026-11-01',version:'folio-shell-v62',results},null,2)+'\n');
console.log(JSON.stringify(results,null,2));
