import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const outDir = process.argv[2];
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const profile = await mkdtemp(join(tmpdir(), 'folio-v92-cdp-'));
const port = 9239;
const browser = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run',
  `--remote-debugging-port=${port}`, '--remote-allow-origins=*',
  `--user-data-dir=${profile}`, '--window-size=390,900', 'about:blank'
], { stdio: 'ignore', windowsHide: true });
let ws;
try {
  let version;
  for (let i = 0; i < 60; i++) {
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; }
    catch { await new Promise(r => setTimeout(r, 250)); }
  }
  if (!version) throw new Error('Chrome DevTools endpoint did not become ready');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('Chrome page target was not created');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  ws.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (!msg.id) return;
    const entry = pending.get(msg.id);
    if (!entry) return;
    pending.delete(msg.id);
    msg.error ? entry.reject(new Error(msg.error.message)) : entry.resolve(msg.result);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.navigate', { url: 'http://127.0.0.1:8767/' });
  await new Promise(r => setTimeout(r, 2500));
  const projectView = await send('Runtime.evaluate', {
    expression: `new Promise(resolve => { const loop = () => { const button = document.querySelector('[data-view="projects"]'); if (button) { button.click(); resolve(true); } else setTimeout(loop, 100); }; loop(); })`,
    awaitPromise: true,
    returnByValue: true
  });
  if (!projectView.result.value) throw new Error('Could not open the Projects view');
  await new Promise(r => setTimeout(r, 500));
  const results = [];
  for (const width of [320, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: true });
    await send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });
    await new Promise(r => setTimeout(r, 350));
    const evaluated = await send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.querySelector('.main-content:has(>.filter-panel)');
        const actions = root?.querySelector('.results-actions');
        const select = actions?.querySelector('.select-visible-control');
        const view = actions?.querySelector('.view-toggle button');
        const reset = actions?.querySelector('#reset-filters');
        const size = el => el ? getComputedStyle(el).fontSize : null;
        const rect = el => { const r=el?.getBoundingClientRect(); return r?{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}:null; };
        return {ready:!!document.querySelector('.filter-panel'),title:document.title,width:innerWidth,visualWidth:Math.round(visualViewport?.width||0),visualScale:visualViewport?.scale||1,scrollWidth:document.documentElement.scrollWidth,selectFont:size(select?.querySelector('span')),viewFont:size(view),resetFont:size(reset),selectRect:rect(select),viewRect:rect(actions?.querySelector('.view-toggle')),resetRect:rect(reset),serviceWorker:!!navigator.serviceWorker?.controller};
      })()`, returnByValue: true
    });
    const metrics = evaluated.result.value;
    const screenshot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, fromSurface: true });
    const name = `web-v92-catalog-${width}x900.png`;
    await writeFile(join(outDir, name), Buffer.from(screenshot.data, 'base64'));
    results.push({ ...metrics, screenshot: name });
  }
  await writeFile(join(outDir, 'results.json'), JSON.stringify({ build: 'folio-shell-v92-mobile-toolbar-readability', checks: results }, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify(results, null, 2));
} finally {
  try { ws?.close(); } catch {}
  browser.kill();
  await new Promise(r => setTimeout(r, 400));
  await rm(profile, { recursive: true, force: true });
}
