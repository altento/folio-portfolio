import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/single-synthetic-v144';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });

const response = await page.goto(baseUrl, { waitUntil: 'networkidle' });
if (!response?.ok()) throw new Error(`App returned HTTP ${response?.status()}`);
const writeResult = await page.evaluate(async () => {
  const response = await fetch('./demo.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Demo seed returned HTTP ${response.status}`);
  const seed = await response.json();
  if (seed.projects.length !== 3) throw new Error(`Expected exactly three demo entries; found ${seed.projects.length}`);
  const project = structuredClone(seed.projects[0]);
  project.title = 'Синтетический тест · один проект';
  project.description = 'Изолированная проверка интерфейса на наборе из одной карточки. Данные созданы для QA и не относятся к реальному портфолио.';
  project.context = 'Проверить, что интерфейс корректно показывает библиотеку из одного кейса.';
  project.role = 'QA-автор';
  project.outcome = 'В списке и сводке остаётся ровно одна синтетическая карточка.';
  project.demo_url = '';
  project.tags = ['QA', 'одна запись'];
  project.featured = true;
  const value = { ...seed, title: 'Тестовое локальное портфолио', developer: { full_name: 'QA Автор', specialization: 'Тестирование интерфейсов' }, projects: [project], next_id: 2, demo: true };
  const db = await new Promise((resolve, reject) => {
    const request = indexedDB.open('folio-workspace', 1);
    request.onupgradeneeded = () => { if (!request.result.objectStoreNames.contains('records')) request.result.createObjectStore('records', { keyPath: 'key' }); };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  const old = await new Promise((resolve, reject) => {
    const request = db.transaction('records', 'readonly').objectStore('records').get('portfolio');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  await new Promise((resolve, reject) => {
    const tx = db.transaction('records', 'readwrite');
    tx.objectStore('records').put({ key: 'portfolio', value, revision: (old?.revision || 0) + 1 });
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error('Isolated test record transaction aborted'));
  });
  db.close();
  return { previousDemoCount: seed.projects.length, persistedProjectCount: value.projects.length, syntheticTitle: project.title };
});

await page.reload({ waitUntil: 'networkidle' });
const dashboard = await page.evaluate(() => ({
  title: document.querySelector('h1')?.textContent?.trim(),
  pageText: document.body.innerText,
  viewport: innerWidth,
  documentWidth: document.documentElement.scrollWidth,
  bodyWidth: document.body.scrollWidth,
}));
const dashboardOk = dashboard.title === 'Ваши проекты, собранные в одном месте.' && dashboard.pageText.includes('01') && dashboard.documentWidth <= dashboard.viewport && dashboard.bodyWidth <= dashboard.viewport;
await page.screenshot({ path: `${out}/single-synthetic-dashboard-v144.png`, fullPage: true });

await page.locator('[data-view="projects"]:visible').first().click();
const cards = page.locator('.project-card');
const projectTitles = await cards.locator('.card-title').allTextContents();
const hasSynthetic = projectTitles.length === 1 && projectTitles[0].includes(writeResult.syntheticTitle);
await page.screenshot({ path: `${out}/single-synthetic-projects-v144.png`, fullPage: true });

const mobile = {};
for (const width of [390, 320]) {
  await page.setViewportSize({ width, height: 844 });
  await page.screenshot({ path: `${out}/single-synthetic-projects-v144-${width}.png`, fullPage: true });
  mobile[width] = await page.evaluate(() => ({ viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth }));
}

const result = {
  date: '2026-11-05',
  build: 'v144 app served on localhost, isolated fresh Chromium context; synthetic case replaces the three demo cases only in that context IndexedDB',
  httpStatus: response.status(),
  writeResult,
  dashboard: { ...dashboard, passed: dashboardOk },
  projectList: { count: projectTitles.length, titles: projectTitles, exactlyOneSyntheticCase: hasSynthetic },
  mobile,
  runtimeErrors: errors,
  userDataChanged: false,
  passed: dashboardOk && hasSynthetic && Object.values(mobile).every(x => x.documentWidth <= x.viewport && x.bodyWidth <= x.viewport) && errors.length === 0,
};
await writeFile(`${out}/single-synthetic-v144-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# Однокейсовый синтетический сценарий — v144\n\nИзолированный свежий Chromium-контекст загрузил три демо-записи, заменил их одной синтетической карточкой через IndexedDB и перезагрузил приложение. Персональный профиль браузера и рабочие базы не читались и не изменялись. Проверены сводка, точное количество карточек и размеры 1440/390/320 CSS px.\n\nРезультат: \`single-synthetic-v144-results.json\`. Снимки: \`single-synthetic-dashboard-v144.png\`, \`single-synthetic-projects-v144.png\` и мобильные варианты.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;
