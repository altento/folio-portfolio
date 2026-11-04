import fs from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const outDir = path.join(root, 'служебные_файлы', 'qa_02-11-2026', 'web-responsive-v116');
const port = 9237;
await fs.mkdir(outDir, { recursive: true });
async function waitForDebug() {
  const until = Date.now() + 12000;
  while (Date.now() < until) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/list`);
      if (r.ok) return await r.json();
    } catch {}
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error('Chrome DevTools endpoint did not become ready');
}
const targets = await waitForDebug();
const target = targets.find(t => t.type === 'page');
if (!target?.webSocketDebuggerUrl) throw new Error('No page target');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, { once: true });
  ws.addEventListener('error', reject, { once: true });
});
let nextId = 0;
const pending = new Map();
ws.addEventListener('message', ev => {
  const msg = JSON.parse(ev.data);
  if (!msg.id) return;
  const p = pending.get(msg.id);
  if (!p) return;
  pending.delete(msg.id);
  msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
});
function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
const delay = ms => new Promise(r => setTimeout(r, ms));
await send('Page.enable');
await send('Runtime.enable');
await send('Network.enable');
await send('Network.setBypassServiceWorker',{bypass:true});
await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });
await delay(5000);
const sizes = [
  { name: 'portrait-320x568', width: 320, height: 568 },
  { name: 'portrait-390x844', width: 390, height: 844 },
  { name: 'landscape-844x390', width: 844, height: 390 },
];
const results = [];
for (const size of sizes) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: size.width, height: size.height, deviceScaleFactor: 1, mobile: true,
  });
  await delay(250);
  const measurement = await send('Runtime.evaluate', {
    expression: `(() => {
      const selectors = ['.portfolio-insights .insight-intro','.portfolio-insights .insight-item-copy p','.portfolio-insights .insight-complete p','.portfolio-insights .status-row','.stat-card>span','.stat-card>small','.storage-reliability-heading span:not(.storage-reliability-indicator)','.storage-meter-caption','.storage-reliability-note'];
      const styles = Object.fromEntries(selectors.map(s => {const e=document.querySelector(s); return [s,e?{fontSize:getComputedStyle(e).fontSize,visible:!!e.getClientRects().length}:null]}));
      return {width:innerWidth,height:innerHeight,documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight,horizontalOverflow:document.documentElement.scrollWidth>innerWidth,serviceWorker:navigator.serviceWorker?.controller?.scriptURL||null,title:document.title,bodyStart:(document.body.innerText||'').slice(0,260),styles};
    })()`, returnByValue: true,
  });
  const value = measurement.result?.value;
  const screenshot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
  const screenshotPath = path.join(outDir, `${size.name}-v116.png`);
  await fs.writeFile(screenshotPath, Buffer.from(screenshot.data, 'base64'));
  results.push({ ...size, measurement: value, screenshot: path.basename(screenshotPath) });
}
await fs.writeFile(path.join(outDir, 'responsive-results-v116.json'), JSON.stringify({ testedAt: new Date().toISOString(), url: 'http://127.0.0.1:8766/', profile: 'isolated temporary Chrome profile', results }, null, 2) + '\n', 'utf8');
await send('Emulation.clearDeviceMetricsOverride').catch(() => {});
ws.close();
console.log(JSON.stringify(results, null, 2));
