import { strict as assert } from 'node:assert';
import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--no-sandbox']});
const checks=[];
try {
  for(const viewport of [{width:320,height:568},{width:1440,height:900}]){
    const context=await browser.newContext({viewport,reducedMotion:'reduce'}),page=await context.newPage();
    await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
    await page.getByRole('button',{name:'Создать проект'}).click();
    await page.waitForFunction(()=>document.querySelector('#project-dialog')?.open&&document.querySelector('#project-dialog')?.dataset.mobileStep==='0');
    const state=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,wizardHidden:document.querySelector('#project-form-wizard').hidden,storyDisplay:getComputedStyle(document.querySelector('[name=context]').closest('.field')).display,backHidden:document.querySelector('#project-form-step-back').hidden,nextHidden:document.querySelector('#project-form-step-next').hidden,submitHidden:document.querySelector('#project-form-submit').hidden}));
    assert.ok(state.documentWidth<=state.width,`horizontal overflow at ${state.width}: ${JSON.stringify(state)}`);
    if(viewport.width===320){assert.equal(state.wizardHidden,false);await page.screenshot({path:'C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_02-11-2026/mobile-case-form-wizard-v105/mobile-320-basics.png'});await page.locator('#project-form-step-next').scrollIntoViewIfNeeded();const nextState=await page.locator('#project-form-step-next').evaluate(el=>({visible:!!(el.offsetWidth||el.offsetHeight),rect:el.getBoundingClientRect().toJSON(),dialog:document.querySelector('#project-dialog').getBoundingClientRect().toJSON()}));assert.equal(nextState.visible,true);assert.ok(nextState.rect.bottom<=nextState.dialog.bottom,`sticky next action outside dialog: ${JSON.stringify(nextState)}`);await page.screenshot({path:'C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_02-11-2026/mobile-case-form-wizard-v105/mobile-320-basics-actions.png'});}
    else {assert.equal(state.wizardHidden,true);assert.equal(state.storyDisplay,'grid');assert.equal(state.backHidden,true);assert.equal(state.nextHidden,true);assert.equal(state.submitHidden,false);await page.screenshot({path:'C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_02-11-2026/mobile-case-form-wizard-v105/desktop-form.png'});}
    checks.push(state);await context.close();
  }
  console.log(JSON.stringify({status:'PASS',checks},null,2));
} finally {await browser.close()}
