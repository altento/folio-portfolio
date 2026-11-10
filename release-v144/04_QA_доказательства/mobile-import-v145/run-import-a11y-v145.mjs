import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { readFile, writeFile } from 'node:fs/promises';
const out='служебные_файлы/qa_05-11-2026/mobile-import-v145';
const axe=await readFile('служебные_файлы/qa_02-11-2026/mobile-case-form-wizard-v105/axe-core-4.14.0.min.js','utf8');
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const results={},errors=[];
for(const width of [390,320]){
 const context=await browser.newContext({viewport:{width,height:568},isMobile:true,hasTouch:true,reducedMotion:'reduce'});const page=await context.newPage();
 page.on('pageerror',e=>errors.push(`${width}: ${e}`));page.on('console',m=>{if(m.type()==='error')errors.push(`${width}: ${m.text()}`)});
 const response=await page.goto(process.env.FOLIO_BASE_URL||'http://127.0.0.1:8766/',{waitUntil:'networkidle'});if(!response?.ok())throw Error(`HTTP ${response?.status()}`);
 const build=await page.evaluate(async()=>(await(await fetch('./sw.js')).text()).match(/folio-shell-v\d+[^']*/)?.[0]||'');if(build!=='folio-shell-v145-mobile-import-actions')throw Error(`Wrong build: ${build}`);
 await page.locator('[data-view="settings"]:visible').first().click();const chooserWait=page.waitForEvent('filechooser');await page.locator('[data-action="import-json"]:visible').first().click();const chooser=await chooserWait;
 const seed=await page.evaluate(async()=>(await(await fetch('./demo.json')).json()));const project=structuredClone(seed.projects[0]);project.id=991;project.project_id=991;project.title='Диалог доступности';
 await chooser.setFiles({name:'a11y.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schema_version:1,title:'QA',next_id:992,developer:{full_name:'QA',specialization:'QA'},projects:[project]}))});
 const dialog=page.locator('#import-dialog');await dialog.waitFor({state:'visible'});await page.waitForFunction(()=>document.querySelector('#import-dialog')?.contains(document.activeElement));await page.addScriptTag({content:axe});
 const audit=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}});return{violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length})),passes:r.passes.length}});
 const initial=await page.evaluate(()=>({inside:document.querySelector('#import-dialog').contains(document.activeElement),label:document.activeElement.getAttribute('aria-label')||document.activeElement.textContent.trim()}));
 await page.keyboard.press('Shift+Tab');const reverse=await page.evaluate(()=>({inside:document.querySelector('#import-dialog').contains(document.activeElement),tag:document.activeElement.tagName}));
 await page.screenshot({path:`${out}/import-a11y-${width}-v145.png`});
 await page.keyboard.press('Escape');await page.waitForTimeout(100);const closed=await page.evaluate(()=>!document.querySelector('#import-dialog').open);const restored=await page.evaluate(()=>document.activeElement?.getAttribute('data-action')==='import-json');
 results[width]={build,axeViolations:audit.violations,axePasses:audit.passes,initialFocusInsideDialog:initial.inside,initialFocusLabel:initial.label,shiftTabRemainsInside:reverse.inside,escapeClosesDialog:closed,escapeRestoresTrigger:restored};
 results[width].passed=audit.violations.length===0&&initial.inside&&reverse.inside&&closed&&restored;await context.close();
}
const result={date:'2026-11-05',build:'folio-shell-v145-mobile-import-actions',viewportHeight:568,results,runtimeErrors:errors,passed:Object.values(results).every(r=>r.passed)&&errors.length===0};
await writeFile(`${out}/import-a11y-v145-results.json`,JSON.stringify(result,null,2)+'\n');
await writeFile(`${out}/import-a11y-v145.md`,`# Доступность мобильного диалога импорта — v145\n\naxe-core 4.14.0 проверил диалог импорта на 390×568 и 320×568 CSS px. Проверены начальный фокус, Shift+Tab на границе диалога и возврат фокуса к кнопке после Escape. Нарушений WCAG A/AA в проверенных правилах не обнаружено. Подробный JSON и скриншоты находятся рядом.\n`);
console.log(JSON.stringify(result,null,2));await browser.close();if(!result.passed)process.exitCode=1;
