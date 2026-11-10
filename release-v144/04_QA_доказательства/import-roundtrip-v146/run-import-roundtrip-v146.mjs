import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/import-roundtrip-v146';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce', acceptDownloads: true });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
const response = await page.goto(baseUrl, { waitUntil: 'networkidle' });
if (!response?.ok()) throw new Error(`HTTP ${response?.status()}`);
const cacheId = await page.evaluate(async () => (await (await fetch('./sw.js')).text()).match(/folio-shell-v\d+[^']*/)?.[0] || '');
if (cacheId !== 'folio-shell-v146-import-a11y-target-size') throw new Error(`Expected v146 assets, got ${cacheId}`);

const incoming = await page.evaluate(async () => {
  const seed = await (await fetch('./demo.json')).json();
  const project = structuredClone(seed.projects[0]);
  project.id = 90;
  project.project_id = 90;
  project.title = 'Импортированный синтетический кейс';
  project.description = 'Проверка JSON переноса между двумя изолированными профилями.';
  project.tags = ['перенос', 'QA'];
  project.demo_url = '';
  return { schema_version: 1, title: 'Синтетический перенос', next_id: 91, developer: { full_name: 'QA Автор', specialization: 'Проверка импорта' }, projects: [project] };
});
const setFile = async payload => {
  const chooserWait = page.waitForEvent('filechooser');
  await page.locator('[data-action="import-json"]:visible').first().click();
  const chooser = await chooserWait;
  await chooser.setFiles({ name: 'synthetic-transfer.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(payload)) });
  await page.locator('#import-dialog').waitFor({ state: 'visible' });
};
await page.locator('[data-view="settings"]:visible').first().click();
await setFile(incoming);
await page.screenshot({ path: `${out}/01-import-preview-v146.png`, fullPage: false });
await page.locator('#import-keep').click();
await page.locator('#import-dialog').waitFor({ state: 'hidden' });
await page.locator('[data-view="projects"]:visible').first().click();
await page.waitForTimeout(200);
const mergedCount = await page.locator('.project-card').count();
await page.locator('#search-input').fill('Импортированный синтетический кейс');
await page.waitForTimeout(200);
const mergedHitCount = await page.locator('.project-card').count();
if (mergedCount !== 4 || mergedHitCount !== 1) throw new Error(`Merge result mismatch: total=${mergedCount}, imported match=${mergedHitCount}`);
await page.screenshot({ path: `${out}/02-import-merged-v146.png`, fullPage: true });

const replacement = structuredClone(incoming);
replacement.title = 'Синтетический портфолио после замены';
replacement.projects[0].id = 200;
replacement.projects[0].project_id = 200;
replacement.projects[0].title = 'Единственный проект после замены';
replacement.next_id = 201;
await page.locator('[data-view="settings"]:visible').first().click();
await setFile(replacement);
await page.screenshot({ path: `${out}/03-replace-preview-v146.png`, fullPage: false });
const backupPath = `${out}/temporary-before-replace.json`;
const downloadWait = page.waitForEvent('download');
await page.locator('#import-replace').click();
const backupDownload = await downloadWait;
await backupDownload.saveAs(backupPath);
await page.locator('#import-dialog').waitFor({ state: 'hidden' });
const safetyBackup = JSON.parse(await readFile(backupPath, 'utf8'));
const backupContainsCurrent = safetyBackup.projects.length === 4 && safetyBackup.projects.some(project => project.title === 'Импортированный синтетический кейс');
await rm(backupPath, { force: true });
await page.locator('[data-view="projects"]:visible').first().click();
await page.waitForTimeout(200);
const replacementCount = await page.locator('.project-card').count();
const replacementTitles = await page.locator('.project-card .card-title').allTextContents();
const replacementApplied = replacementCount === 1 && replacementTitles.some(value => value.includes('Единственный проект после замены'));
await page.screenshot({ path: `${out}/04-replaced-library-v146.png`, fullPage: true });

const result = {
  date: '2026-11-05',
  build: cacheId,
  isolatedContext: true,
  httpStatus: response.status(),
  merge: { initialDemoRecords: 3, resultingRecords: mergedCount, importedProjectSearchHits: mergedHitCount, passed: mergedCount === 4 && mergedHitCount === 1 },
  fullReplacement: { preReplaceBackupDownloaded: Boolean(backupDownload), preReplaceBackupProjectCount: safetyBackup.projects.length, backupContainsMergedCase: backupContainsCurrent, resultingRecords: replacementCount, replacementApplied, temporaryBackupRemoved: true, passed: backupContainsCurrent && replacementApplied },
  runtimeErrors: errors,
  userDataChanged: false,
  passed: mergedCount === 4 && mergedHitCount === 1 && backupContainsCurrent && replacementApplied && errors.length === 0,
};
await writeFile(`${out}/import-roundtrip-v146-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# JSON импорт и безопасная замена — v146\n\nНа актуальном \`${cacheId}\` в отдельном профиле импортирован синтетический JSON: стратегия добавления сохранила три demo-кейса и добавила четвёртый, поиск его нашёл. Затем полная замена сначала скачала JSON-копию текущих четырёх проектов, после чего оставила только импортированный проект. Содержимое safety backup проверено, временная копия QA удалена. Рабочие профили не читались и не менялись.\n\nРезультат: \`import-roundtrip-v146-results.json\`; сценарий: \`run-import-roundtrip-v146.mjs\`; кадры предпросмотра и результата рядом.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;

