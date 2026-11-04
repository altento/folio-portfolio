import fs from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const outDir = path.join(root, 'служебные_файлы', 'qa_02-11-2026', 'web-showcase-v117');
const port = 9237;
await fs.mkdir(outDir, { recursive: true });
const response = await fetch(`http://127.0.0.1:${port}/json/list`);
if (!response.ok) throw new Error(`Chrome DevTools unavailable: ${response.status}`);
const target = (await response.json()).find(item => item.type === 'page');
if (!target?.webSocketDebuggerUrl) throw new Error('No Chrome page target');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', reject, { once: true });
});
let sequence = 0;
const pending = new Map();
ws.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (!message.id) return;
  const callbacks = pending.get(message.id);
  if (!callbacks) return;
  pending.delete(message.id);
  message.error ? callbacks.reject(new Error(message.error.message)) : callbacks.resolve(message.result);
});
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++sequence;
  pending.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params }));
});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');
await send('Network.setBypassServiceWorker', { bypass: true });
await send('Network.setCacheDisabled', { cacheDisabled: true });
await send('Page.navigate', { url: 'http://127.0.0.1:8766/?build=v117' });
await delay(1800);
const generated = await send('Runtime.evaluate', {
  expression: `import('./core.js?build=v117').then(({normalizeProject,staticShowcaseExport})=>{const project=normalizeProject({id:117,type:'Веб-приложение',title:'История без незаполненных блоков',description:'Пустые необязательные сведения не должны появляться в готовом портфолио.',created_at:'2026-11-02',status:'Завершён',technologies:[],page_count:1,featured:true,role:'',outcome:'',context:'Цельный пример кейса',solution:'',process:'',metrics:'',tags:[],gallery_images:[]});const model={title:'Folio · Демонстрация',developer:{full_name:'Мария Демонстрация',specialization:'Веб-разработчик',introduction:'Работы, в которых важны ясность, аккуратность и результат.'},projects:[project]};const html=staticShowcaseExport(model);const blob=new Blob([html],{type:'text/html'});location.href=URL.createObjectURL(blob);return{title:project.title,role:project.role,technologies:project.technologies.length}})`,
  awaitPromise: true,
  returnByValue: true,
});
if (generated.exceptionDetails) throw new Error(generated.exceptionDetails.text);
await delay(1200);
const verify = await send('Runtime.evaluate', { expression: `({title:document.title,hasFacts:!!document.querySelector('.facts'),facts:document.querySelector('.facts')?.innerText||'',placeholders:/Не указана|Не указаны/.test(document.body.innerText),body:document.body.innerText.slice(0,800),viewport:[innerWidth,innerHeight]})`, returnByValue: true });
console.log('Showcase check:', JSON.stringify(verify.result?.value));
if (verify.result?.value?.hasFacts || verify.result?.value?.placeholders) throw new Error('Empty facts remained in exported showcase');
for (const viewport of [{name:'desktop',width:1440,height:1000,mobile:false},{name:'mobile-390',width:390,height:844,mobile:true}]) {
  await send('Emulation.setDeviceMetricsOverride', { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.mobile });
  await delay(250);
  const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: true });
  await fs.writeFile(path.join(outDir, `showcase-${viewport.name}-v117.png`), Buffer.from(shot.data, 'base64'));
}
await fs.writeFile(path.join(outDir, 'showcase-v117-results.json'), JSON.stringify({ generated: generated.result.value, verify: verify.result.value, screenshots: ['showcase-desktop-v117.png','showcase-mobile-390-v117.png'] }, null, 2) + '\n', 'utf8');
await send('Emulation.clearDeviceMetricsOverride');
ws.close();
console.log(JSON.stringify({ generated: generated.result.value, verify: verify.result.value, outDir }, null, 2));
