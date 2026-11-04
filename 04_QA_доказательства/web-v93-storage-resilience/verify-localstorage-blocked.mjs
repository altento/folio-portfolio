import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const output = process.argv[2];
if (!output) throw new Error('Pass the evidence output directory as the first argument.');
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const profile = await mkdtemp(join(tmpdir(), 'folio-v93-storage-'));
const port = 9241;
const browser = spawn(chromePath, ['--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run', `--remote-debugging-port=${port}`, '--remote-allow-origins=*', `--user-data-dir=${profile}`, '--window-size=1440,1000', 'about:blank'], { stdio: 'ignore', windowsHide: true });
let socket;
try {
  let version;
  for (let attempt = 0; attempt < 60; attempt++) {
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; }
    catch { await new Promise(resolve => setTimeout(resolve, 250)); }
  }
  if (!version) throw new Error('Chrome DevTools endpoint did not become ready.');
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find(target => target.type === 'page');
  if (!page) throw new Error('Chrome page target was not created.');
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const entry = pending.get(message.id);
    if (!entry) return;
    pending.delete(message.id);
    message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `Object.defineProperty(window, 'localStorage', { configurable: false, get() { throw new DOMException('Blocked by QA', 'SecurityError'); } });` });
  await send('Page.navigate', { url: 'http://127.0.0.1:8766/?build=93#dashboard' });
  let state;
  for (let attempt = 0; attempt < 80; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 250));
    state = await send('Runtime.evaluate', { expression: `(() => ({title:document.title,heading:document.querySelector('#main-content h1')?.textContent||'',fatal:Boolean(document.querySelector('.fatal-state')),cards:document.querySelectorAll('.project-card').length,serviceWorkerController:Boolean(navigator.serviceWorker?.controller),preferencesFallback:typeof createPreferenceStore}))()`, returnByValue: true });
    const value = state.result?.value;
    if (value?.heading && !value.heading.includes('Открываем')) break;
  }
  const result = state.result.value;
  if (result.fatal || result.cards !== 3 || !result.heading.includes('Ваши проекты')) throw new Error(`Portfolio failed to start with blocked localStorage: ${JSON.stringify(result)}`);
  await new Promise(resolve => setTimeout(resolve, 500));
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, fromSurface: true });
  await writeFile(join(output, 'web-v93-dashboard-localstorage-blocked.png'), Buffer.from(shot.data, 'base64'));
  await writeFile(join(output, 'results.json'), JSON.stringify({ test: 'localStorage getter throws SecurityError at document start', ...result, passed: true, viewport: { width: 1440, height: 1000 } }, null, 2) + '\n');
  console.log(JSON.stringify({ ...result, passed: true }, null, 2));
} finally {
  socket?.close();
  browser.kill();
  await rm(profile, { recursive: true, force: true });
}
