import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const out='C:/Users/Windows-10/Desktop/Портфолио_веб-разработчика/служебные_файлы/qa_02-11-2026/mobile-case-form-wizard-v105';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--no-sandbox']});
const records=[];
try {
 for (const viewport of [{width:1440,height:1000,name:'dashboard-desktop-v106.png'},{width:390,height:844,name:'dashboard-mobile-v106.png'}]) {
  const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},reducedMotion:'reduce',serviceWorkers:'block'});
  const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
  for(const image of await page.locator('img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(el=>el.decode().catch(()=>{}));}
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.waitForTimeout(400);
  const visuals=await page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight,documentWidth:document.documentElement.scrollWidth},images:[...document.images].map(i=>({src:i.currentSrc||i.src,loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight,alt:i.alt})),projectCards:document.querySelectorAll('.project-card').length,heading:document.querySelector('h1')?.innerText}));
  await page.screenshot({path:`${out}/${viewport.name}`,fullPage:false});
  records.push({name:viewport.name,...visuals,pageErrors:errors}); await context.close();
 }
 console.log(JSON.stringify({status:'PASS',records},null,2));
} finally {await browser.close()}
