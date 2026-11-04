import { strict as assert } from 'node:assert';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const out=fileURLToPath(new URL('.',import.meta.url));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--no-sandbox']});
try{
 const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});const page=await context.newPage();
 await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
 await page.getByRole('button',{name:'Создать проект'}).click();
 await page.locator('[name=title]').fill('Keyboard focus audit');await page.locator('#project-form [name=description]').fill('Проверка видимого фокуса при клавиатурном переходе между шагами.');
 await page.locator('#project-form-step-next').focus();await page.keyboard.press('Enter');
 await page.waitForFunction(()=>document.querySelector('#project-dialog')?.dataset.mobileStep==='1');
 const focus=await page.evaluate(()=>{const el=document.activeElement,s=getComputedStyle(el);return {step:document.querySelector('#project-dialog').dataset.mobileStep,activeId:el.id,activeText:el.textContent.trim(),outlineStyle:s.outlineStyle,outlineWidth:s.outlineWidth,outlineColor:s.outlineColor,rect:el.getBoundingClientRect().toJSON()}});
 assert.equal(focus.activeId,'project-form-step-title');assert.equal(focus.outlineStyle,'solid');assert.equal(focus.outlineWidth,'2px');
 await page.screenshot({path:out+'\\keyboard-step-2-focus-v109.png'});
 await page.keyboard.press('Tab');
 const next=await page.evaluate(()=>({id:document.activeElement.id,name:document.activeElement.getAttribute('name'),text:document.activeElement.getAttribute('aria-label')||document.activeElement.textContent.trim(),insideDialog:!!document.activeElement.closest('#project-dialog'),visible:document.activeElement.getClientRects().length>0}));
 assert.equal(next.insideDialog,true,'Tab after the step heading should stay within the open dialog');assert.equal(next.visible,true,'Tab should move to a visible control');
 await page.setViewportSize({width:1024,height:900});await page.waitForTimeout(100);const desktop=await page.evaluate(()=>({insideDialog:!!document.activeElement.closest('#project-dialog'),visible:document.activeElement.getClientRects().length>0}));assert.equal(desktop.insideDialog,true);assert.equal(desktop.visible,true);
 await page.locator('#gallery-files').focus();await page.setViewportSize({width:390,height:844});await page.waitForTimeout(100);const mobile=await page.evaluate(()=>({id:document.activeElement.id,insideDialog:!!document.activeElement.closest('#project-dialog'),visible:document.activeElement.getClientRects().length>0}));assert.equal(mobile.id,'project-form-step-title','focus hidden by the breakpoint should move to the current visible step heading');assert.equal(mobile.insideDialog,true);assert.equal(mobile.visible,true);
 const result={status:'PASS',transition:'Enter on Next',focusedStepHeading:focus,tabTargetAfterHeading:next,resizeDesktop:desktop,resizeMobile:mobile,noDataMutation:true};
 await writeFile(out+'\\keyboard-focus-v109-results.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));await context.close();
}finally{await browser.close()}
