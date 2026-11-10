import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const port=process.env.FOLIO_PORT,out=process.env.FOLIO_QA_DIR,axe=await readFile(process.env.FOLIO_AXE_PATH,'utf8');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const errors=[],badResponses=[],states={};
for(const theme of ['light','dark'])for(const width of [1440,390,320]){
  const mobile=width<821;
  const context=await browser.newContext({viewport:{width,height:844},isMobile:mobile,hasTouch:mobile,reducedMotion:'reduce'});
  await context.addInitScript(value=>localStorage.setItem('folio-theme',value),theme);
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  page.on('response',r=>{if(r.status()>=400)badResponses.push({status:r.status(),url:r.url()})});
  await page.route('**/desktop-seed.json',route=>route.fulfill({status:204,body:''}));
  await page.goto(`http://127.0.0.1:${port}/?folio-desktop=1`,{waitUntil:'networkidle'});
  await page.addScriptTag({content:axe});
  const create=page.getByRole('button',{name:/Новый проект|Добавить проект/}).filter({visible:true}).first();
  await create.click();
  const dialog=page.locator('#project-dialog');
  await dialog.waitFor({state:'visible'});
  if(mobile){
    await page.locator('#project-form input[name="title"]').fill('Изолированный QA-проект');
    await page.locator('#project-form textarea[name="description"]').fill('Тестовый текст формы, не будет сохранён в библиотеку.');
  }
  const steps=mobile?3:1;
  for(let step=0;step<steps;step++){
    await page.waitForTimeout(80);
    const result=await page.evaluate(async()=>{
      const d=document.querySelector('#project-dialog'),a=await axe.run(d);
      const controls=[...d.querySelectorAll('input:not([type=hidden]),select,textarea,button')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');
      const unnamed=controls.filter(e=>!(e.getAttribute('aria-label')||e.labels?.length||e.textContent.trim()||e.getAttribute('title'))).map(e=>e.outerHTML.slice(0,160));
      const r=d.getBoundingClientRect();
      return {theme:document.documentElement.dataset.theme,viewport:innerWidth,dialog:{x:Math.round(r.x),width:Math.round(r.width),right:Math.round(r.right),scrollWidth:d.scrollWidth,clientWidth:d.clientWidth},formTitle:document.querySelector('#project-dialog-title')?.innerText||'',step:Number(d.dataset.mobileStep||0),stepTitle:document.querySelector('#project-form-step-title')?.innerText||'',visibleControls:controls.length,unnamed,axeViolations:a.violations.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length,targets:v.nodes.slice(0,5).map(n=>n.target)})),documentScrollWidth:document.documentElement.scrollWidth,bodyScrollWidth:document.body.scrollWidth};
    });
    const key=`${theme}-${width}-${mobile?`step-${step+1}`:'desktop'}`;
    result.expectedStep=step;
    result.stepCorrect=result.step===step;
    states[key]=result;
    await page.screenshot({path:`${out}/project-form-${key}.png`,fullPage:true});
    if(mobile&&step<steps-1)await page.locator('#project-form-step-next').click();
  }
  await page.keyboard.press('Escape');
  await context.close();
}
const all=Object.values(states);
const summary={count:all.length,allThemeCorrect:all.every(x=>x.theme==='light'||x.theme==='dark'),allWizardStepsCorrect:all.every(x=>x.stepCorrect),allDialogFits:all.every(x=>x.dialog.x>=0&&x.dialog.right<=x.viewport&&x.dialog.scrollWidth<=x.dialog.clientWidth),noPageOverflow:all.every(x=>x.documentScrollWidth<=x.viewport&&x.bodyScrollWidth<=x.viewport),allControlsNamed:all.every(x=>!x.unnamed.length),allAxeClean:all.every(x=>!x.axeViolations.length),noRuntimeErrors:!errors.length&&!badResponses.length};
const result={date:'2026-11-05',build:'packaged Windows WebView2 v142; isolated Playwright Chromium profile',matrix:'project creation dialog; light/dark; 1440 desktop and 390/320 phone; all 3 phone wizard steps',states,summary,errors,badResponses,passed:all.length===14&&Object.values(summary).every(Boolean)};
await writeFile(`${out}/project-form-audit-v142-results.json`,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({passed:result.passed,summary,failures:Object.fromEntries(Object.entries(states).filter(([,x])=>x.axeViolations.length||x.unnamed.length||x.dialog.x<0||x.dialog.right>x.viewport||x.dialog.scrollWidth>x.dialog.clientWidth||x.documentScrollWidth>x.viewport||x.bodyScrollWidth>x.viewport)),errors,badResponses},null,2));
await browser.close();
if(!result.passed)process.exitCode=1;
