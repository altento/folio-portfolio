const endpoint = process.env.DEVTOOLS_URL || 'http://127.0.0.1:9230/json';
const targets = await (await fetch(endpoint)).json();
const target = targets.find(item => item.type === 'page' && item.url.startsWith('https://localhost'));
if (!target) throw new Error('Folio WebView target not found');
const socket = new WebSocket(target.webSocketDebuggerUrl);
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
await send('Runtime.enable');
await send('Network.enable');
await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0, connectionType: 'none' });
await send('Page.reload', { ignoreCache: false });
const response = await send('Runtime.evaluate', {
  expression: `new Promise(async resolve => {
    const wait = selector => new Promise(done => { const check = () => document.querySelector(selector) ? done() : setTimeout(check,100); check(); });
    await wait('#main-content h1');
    await new Promise(done => setTimeout(done,500));
    const cachesBefore = await caches.keys();
    const button = document.querySelector('.mobile-nav [data-view="projects"]') || document.querySelector('.side-nav [data-view="projects"]');
    button?.click();
    await wait('.filter-panel');
    const cacheNames = await caches.keys();
    resolve({url:location.href,title:document.title,heading:document.querySelector('#main-content h1')?.textContent,offline:!navigator.onLine,serviceWorkerController:Boolean(navigator.serviceWorker?.controller),cacheNames,cachesBefore,viewportWidth:innerWidth,documentWidth:document.documentElement.scrollWidth,projectCards:document.querySelectorAll('.project-card').length,projectsView:Boolean(document.querySelector('.filter-panel'))});
  })`,
  awaitPromise: true,
  returnByValue: true
});
const result = response.result.value;
socket.close();
console.log(JSON.stringify(result, null, 2));
if (!result.offline || !result.serviceWorkerController || !result.cacheNames.includes('folio-shell-v93-storage-resilience') || !result.projectsView || result.projectCards !== 3 || result.documentWidth > result.viewportWidth) process.exitCode = 1;
