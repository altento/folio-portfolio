import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, writeFile, rm } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/user-flow-v144';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/';
const title = 'QA flow v144 · кейс для проверки';
const description = 'Синтетический сценарий: создание, поиск, изменение, резервная копия и восстановление после удаления.';
const editedDescription = 'Изменённое описание сохраняется после перезапуска страницы.';
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
if (cacheId !== 'folio-shell-v144-tag-sorting') throw new Error(`Expected v144 assets, got ${cacheId}`);
await page.screenshot({ path: `${out}/01-dashboard-v144.png`, fullPage: true });

await page.locator('[data-action="new-project"]:visible').first().click();
await page.waitForFunction(() => document.querySelector('#project-dialog')?.open);
await page.locator('#project-form [name="title"]').fill(title);
await page.locator('#project-form [name="description"]').fill(description);
await page.locator('#project-form [name="context"]').fill('Проверить основные действия автора с одной новой записью.');
await page.locator('#project-form [name="role"]').fill('QA-автор');
await page.locator('#project-form [name="outcome"]').fill('Кейс остаётся после перезагрузки и попадает в JSON backup.');
await page.locator('#project-form-submit').click();
await page.waitForFunction(() => !document.querySelector('#project-dialog')?.open);

await page.locator('[data-view="projects"]:visible').first().click();
const search = page.locator('#search-input');
await search.fill(title);
await page.waitForTimeout(300);
const searchCount = await page.locator('.project-card').count();
if (searchCount !== 1) throw new Error(`Expected 1 search hit, got ${searchCount}`);
await page.screenshot({ path: `${out}/02-search-v144.png`, fullPage: true });
await page.locator('[data-detail]').filter({ hasText: title }).click();
await page.locator('#detail-dialog').waitFor({ state: 'visible' });
await page.screenshot({ path: `${out}/03-detail-v144.png`, fullPage: false });

await page.locator('#detail-dialog [data-edit]').click();
await page.locator('#project-dialog').waitFor({ state: 'visible' });
if (await page.locator('#project-form [name="description"]').inputValue() !== description) throw new Error('Edit form lost the original description');
await page.locator('#project-form [name="description"]').fill(editedDescription);
await page.locator('#project-form-submit').click();
await page.waitForFunction(() => !document.querySelector('#project-dialog')?.open);
await page.reload({ waitUntil: 'networkidle' });
await page.locator('[data-view="projects"]:visible').first().click();
await page.locator('#search-input').fill(title);
await page.waitForTimeout(300);
await page.locator('[data-detail]').filter({ hasText: title }).click();
await page.locator('#detail-dialog').waitFor({ state: 'visible' });
const persistence = (await page.locator('#detail-dialog').innerText()).includes(editedDescription);
if (!persistence) throw new Error('Edited description was not persisted after reload');
await page.screenshot({ path: `${out}/04-persisted-detail-v144.png`, fullPage: false });
await page.locator('#detail-dialog [data-close-dialog]').click();

await page.locator('[data-view="settings"]:visible').first().click();
const backupPath = `${out}/temporary-backup.json`;
const downloadEvent = page.waitForEvent('download');
await page.locator('[data-action="export-json"]:visible').click();
const download = await downloadEvent;
await download.saveAs(backupPath);
const backup = JSON.parse(await (await import('node:fs/promises')).readFile(backupPath, 'utf8'));
const backedUpProject = backup.projects.find(project => project.title === title);
const backupValid = Boolean(backedUpProject && backedUpProject.description === editedDescription);
await rm(backupPath, { force: true });
if (!backupValid) throw new Error('Downloaded JSON backup did not contain the edited synthetic project');

await page.locator('[data-view="projects"]:visible').first().click();
await page.locator('#search-input').fill(title);
await page.waitForTimeout(250);
await page.locator('[data-detail]').filter({ hasText: title }).click();
await page.locator('#detail-dialog').waitFor({ state: 'visible' });
page.once('dialog', dialog => dialog.accept());
await page.locator('#detail-dialog [data-delete]').click();
await page.locator('#detail-dialog').waitFor({ state: 'hidden' });
await page.waitForTimeout(100);
const undoButton = page.getByRole('button', { name: 'Отменить', exact: true });
const undoAvailable = await undoButton.isVisible().catch(() => false);
if (!undoAvailable) throw new Error('Delete undo action was not shown');
await undoButton.click();
await page.waitForTimeout(200);
await page.locator('#search-input').fill(title);
await page.waitForTimeout(250);
const restoredCount = await page.locator('.project-card').count();
const noErrors = errors.length === 0;
const result = {
  date: '2026-11-05',
  build: cacheId,
  isolatedContext: true,
  httpStatus: response.status(),
  create: true,
  search: { matchingCards: searchCount, passed: searchCount === 1 },
  editAndReload: { persisted: persistence, passed: persistence },
  jsonBackup: { downloaded: true, containsEditedProject: backupValid, temporaryFileRemoved: true, passed: backupValid },
  deleteUndo: { undoAvailable, restoredMatchingCards: restoredCount, passed: undoAvailable && restoredCount === 1 },
  runtimeErrors: errors,
  userDataChanged: false,
  passed: searchCount === 1 && persistence && backupValid && undoAvailable && restoredCount === 1 && noErrors,
};
await writeFile(`${out}/user-flow-v144-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# Сквозной поток кейса — v144\n\nВ изолированном Chromium-контексте на сборке \`${cacheId}\` проверены создание проекта, поиск, детали, редактирование, перезагрузка, JSON backup с точной сверкой изменений и удаление с восстановлением через Undo. Временный backup-файл удалён; профиль и пользовательские данные не затронуты.\n\nРезультат: \`user-flow-v144-results.json\`; воспроизводимый сценарий: \`run-user-flow-v144.mjs\`; кадры сценария лежат рядом.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;
