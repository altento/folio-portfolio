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
  const wait = pending.get(message.id);
  if (!wait) return;
  pending.delete(message.id);
  message.error ? wait.reject(new Error(message.error.message)) : wait.resolve(message.result);
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++nextId;
  pending.set(id, { resolve, reject });
  socket.send(JSON.stringify({ id, method, params }));
});
await send('Runtime.enable');
const response = await send('Runtime.evaluate', {
  expression: `(() => {
    const actions = document.querySelector('.results-actions');
    const select = actions?.querySelector('.select-visible-control span');
    const view = actions?.querySelector('.view-toggle button');
    const reset = actions?.querySelector('#reset-filters');
    return {
      url: location.href,
      title: document.title,
      projectsView: !!document.querySelector('.filter-panel'),
      viewportWidth: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      serviceWorkerController: !!navigator.serviceWorker?.controller,
      selectFont: select ? getComputedStyle(select).fontSize : null,
      viewFont: view ? getComputedStyle(view).fontSize : null,
      resetFont: reset ? getComputedStyle(reset).fontSize : null,
      projectCards: document.querySelectorAll('.project-card').length
    };
  })()`,
  returnByValue: true
});
const result = response.result.value;
socket.close();
console.log(JSON.stringify(result, null, 2));
if (!result.projectsView || !result.serviceWorkerController || result.documentWidth > result.viewportWidth) process.exitCode = 1;
