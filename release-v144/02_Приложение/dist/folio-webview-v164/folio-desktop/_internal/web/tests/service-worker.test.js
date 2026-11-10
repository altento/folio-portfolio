import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';

const serviceWorkerSource = await readFile(new URL('../sw.js', import.meta.url), 'utf8');
const offlinePageSource = await readFile(new URL('../offline.html', import.meta.url), 'utf8');

function createServiceWorkerHarness({ scope, entries }) {
  const listeners = new Map();
  const matchCalls = [];
  const cache = {
    async match(request, options = {}) {
      const url = new URL(typeof request === 'string' ? request : request.url, scope);
      if (options.ignoreSearch) url.search = '';
      matchCalls.push({ url: url.href, options });
      return entries.get(url.href);
    },
    async put() {},
  };
  const sandbox = {
    URL,
    Response: { error: () => ({ type: 'error' }) },
    caches: { open: async () => cache },
    fetch: async () => { throw new Error('network offline'); },
    self: {
      location: { origin: new URL(scope).origin },
      registration: { scope },
      addEventListener: (name, listener) => listeners.set(name, listener),
    },
  };
  vm.runInNewContext(serviceWorkerSource, sandbox, { filename: 'sw.js' });
  return {
    matchCalls,
    async fetchNavigation(url) {
      let responsePromise;
      listeners.get('fetch')({
        request: { method: 'GET', mode: 'navigate', url },
        respondWith(promise) { responsePromise = promise; },
      });
      return responsePromise;
    },
  };
}

test('offline navigation with a query string reuses the cached app root', async () => {
  const scope = 'https://folio.example/folio/';
  const appShell = { kind: 'app-shell' };
  const harness = createServiceWorkerHarness({
    scope,
    entries: new Map([[scope, appShell]]),
  });

  const response = await harness.fetchNavigation(`${scope}?build=68`);

  assert.equal(response, appShell);
  assert.equal(harness.matchCalls[0].url, scope);
  assert.equal(harness.matchCalls[0].options.ignoreSearch, true);
});

test('uncached offline paths show the fallback page instead of a broken app shell', async () => {
  const scope = 'https://folio.example/folio/';
  const offlinePage = { kind: 'offline-page' };
  const harness = createServiceWorkerHarness({
    scope,
    entries: new Map([[new URL('./offline.html', scope).href, offlinePage]]),
  });

  const response = await harness.fetchNavigation(`${scope}projects/saved?view=cards`);

  assert.equal(response, offlinePage);
  assert.equal(harness.matchCalls.at(-1).url, new URL('./offline.html', scope).href);
});

test('offline page returns to the registered app scope with a relative fallback', () => {
  assert.match(offlinePageSource, /href="\.\/"/);
  assert.match(offlinePageSource, /registration\.scope/);
  assert.doesNotMatch(offlinePageSource, /href="\/"/);
});

test('desktop seed and recovery endpoints bypass the service worker cache', () => {
  assert.match(serviceWorkerSource, /\['\/desktop-seed\.json','\/desktop-recovery\.json'\][\s\S]*?respondWith\(fetch\(new Request\(request,\{cache:'no-store'\}\)\)\)/,
    'desktop-only data endpoints must always reach the loopback host and stay out of the PWA cache');
  assert.match(serviceWorkerSource, /folio-shell-v161-accessible-vector-controls/);
});
