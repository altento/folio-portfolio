import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/effective-zoom-v144';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 720, height: 450 }, reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
const response = await page.goto(baseUrl, { waitUntil: 'networkidle' });
if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
const routes = ['dashboard', 'projects', 'showcase', 'settings'];
const results = { light: [], dark: [] };
for (const theme of ['light', 'dark']) {
  await page.evaluate(theme => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#202126' : '#f5f5f2');
  }, theme);
  for (const route of routes) {
    await page.locator(`[data-view="${route}"]:visible`).first().click();
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForTimeout(50);
    const state = await page.evaluate(() => {
      const viewport = { width: innerWidth, height: innerHeight };
      const nav = [...document.querySelectorAll('nav')].map(el => ({ el, rect: el.getBoundingClientRect(), style: getComputedStyle(el) }))
        .filter(x => x.style.position === 'fixed' && x.rect.top >= viewport.height / 2 && x.rect.bottom >= viewport.height - 2)
        .sort((a, b) => a.rect.top - b.rect.top)[0];
      const controls = [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
        .filter(el => !el.closest('nav') && !el.matches('input[type="file"]') && !el.hidden && getComputedStyle(el).visibility !== 'hidden' && getComputedStyle(el).display !== 'none' && getComputedStyle(el).opacity !== '0')
        .map(el => ({ label: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 48) || el.id, rect: el.getBoundingClientRect() }))
        .filter(x => x.rect.width > 0 && x.rect.height > 0);
      const last = controls.sort((a, b) => b.rect.bottom - a.rect.bottom)[0];
      const heading = document.querySelector('main h1')?.textContent?.trim() || document.querySelector('h1')?.textContent?.trim() || '';
      return { viewport, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, heading, navTop: nav?.rect.top ?? null, lastControlBottom: last?.rect.bottom ?? null, lastControl: last?.label ?? null, horizontalOverflow: document.documentElement.scrollWidth > innerWidth || document.body.scrollWidth > innerWidth, bottomNavOverlap: Boolean(nav && last && last.rect.bottom > nav.rect.top + 1) };
    });
    (theme === 'light' ? results.light : results.dark).push({ route, ...state });
    if (theme === 'light' && route === 'projects') await page.screenshot({ path: `${out}/projects-effective-zoom-720x450-v144.png`, fullPage: true });
  }
}
const result = {
  date: '2026-11-05',
  build: 'v144 localhost app in isolated Chromium context, reduced effective viewport approximating desktop 200% zoom',
  viewportCssPx: [720, 450],
  note: 'Effective reflow check; not a native browser zoom setting or physical OS magnifier test.',
  httpStatus: response.status(),
  routes: results,
  runtimeErrors: errors,
  userDataChanged: false,
  passed: [...results.light, ...results.dark].length === 8 && [...results.light, ...results.dark].every(x => !x.horizontalOverflow && !x.bottomNavOverlap && x.navTop !== null && x.lastControlBottom !== null) && errors.length === 0,
};
await writeFile(`${out}/effective-zoom-v144-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# Эффективный reflow при увеличении — v144\n\nВосемь состояний: четыре маршрута × светлая/тёмная тема на viewport 720×450 CSS px (эквивалентный reflow desktop при увеличении 200%). Горизонтальное переполнение и перекрытие последнего управления закреплённой нижней навигацией проверены по DOM-геометрии. Это не нативная настройка browser zoom или системного увеличителя. Рабочие данные не менялись.\n\nРезультаты: \`effective-zoom-v144-results.json\`; кадр: \`projects-effective-zoom-720x450-v144.png\`.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;
