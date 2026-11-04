import { strict as assert } from 'node:assert';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const here=fileURLToPath(new URL('.',import.meta.url));
const axe=await readFile(here+'\\axe-core-4.14.0.min.js','utf8');
const tags=['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice'];
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--no-sandbox']});
const scans={},errors=[];
async function scan(page,name){const raw=await page.evaluate(async tags=>{const r=await axe.run(document,{runOnly:{type:'tag',values:tags}});return {version:axe.version,violations:r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(x=>x.id),passes:r.passes.length}},tags);scans[name]=raw;}
try{
 const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});await page.addScriptTag({content:axe});
 await scan(page,'dashboard_mobile');
 await page.getByRole('button',{name:'Создать проект'}).click();await page.locator('#project-form-wizard').waitFor({state:'visible'});await scan(page,'form_step_1_mobile');
 const basic=await page.evaluate(()=>({wizardLabel:document.querySelector('#project-form-wizard')?.getAttribute('aria-labelledby'),progress:document.querySelector('#project-form-step-progress')?.outerHTML,stepTitle:document.querySelector('#project-form-step-title')?.textContent,hiddenStory:!document.querySelector('[name=context]').checkVisibility(),visibleControls:[...document.querySelectorAll('#project-form input:not([type=hidden]),#project-form select,#project-form textarea')].filter(el=>el.checkVisibility()).map(el=>({id:el.id,name:el.name,labels:el.labels?.length||0,required:el.required}))}));
 await page.locator('[name=title]').fill('Accesibilidad QA');await page.locator('#project-form [name=description]').fill('Validación de accesibilidad y etiquetas.');await page.getByRole('button',{name:/Далее/}).click();await scan(page,'form_step_2_mobile');
 await page.getByRole('button',{name:/Далее/}).click();await scan(page,'form_step_3_mobile');
 const mobileFocus=await page.evaluate(()=>({stepHeading:document.querySelector('#project-form-step-title')?.textContent,activeElement:document.activeElement?.outerHTML?.slice(0,240),progressNow:document.querySelector('#project-form-step-progress')?.getAttribute('aria-valuenow'),progressText:document.querySelector('#project-form-step-progress')?.getAttribute('aria-valuetext'),visibleControls:[...document.querySelectorAll('#project-form input:not([type=hidden]),#project-form select,#project-form textarea')].filter(el=>el.checkVisibility()).map(el=>({id:el.id,name:el.name,labels:el.labels?.length||0,required:el.required}))}));
 await context.close();
 const desktopContext=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});const desktop=await desktopContext.newPage();desktop.on('pageerror',e=>errors.push(e.message));await desktop.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});await desktop.addScriptTag({content:axe});await desktop.getByRole('button',{name:'Создать проект'}).click();await scan(desktop,'form_desktop');await desktopContext.close();
 const violations=Object.values(scans).reduce((sum,s)=>sum+s.violations.length,0);const result={status:violations===0&&errors.length===0?'PASS':'REVIEW_REQUIRED',axeCore:'4.14.0',tags,scans,totalViolations:violations,pageErrors:errors,manualLimit:'No physical screen reader, TalkBack, switch control, or direct OS text scaling was tested.',formStructure:{step1:basic,step3:mobileFocus}};
 await writeFile(here+'\\a11y-results-v109.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,totalViolations:violations,pageErrors:errors,scanCounts:Object.fromEntries(Object.entries(scans).map(([k,v])=>[k,{violations:v.violations.length,passes:v.passes,incomplete:v.incomplete.length}])),step1:basic,step3:mobileFocus},null,2));assert.equal(violations,0,'axe found accessibility violations');assert.deepEqual(errors,[]);
}finally{await browser.close()}
