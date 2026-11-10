import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/keyboard-import-v144';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/?folio-desktop=1';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
const response = await page.goto(baseUrl, { waitUntil: 'networkidle' });
if (!response?.ok()) throw new Error(`App returned HTTP ${response?.status()}`);
await page.locator('[data-view="settings"]:visible').first().click();
const opener = page.locator('[data-action="import-json"]:visible').first();
await opener.scrollIntoViewIfNeeded();
const chooserPromise = page.waitForEvent('filechooser');
await opener.click();
const chooser = await chooserPromise;
await chooser.setFiles({ name: 'synthetic-empty-backup.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ schema_version: 1, projects: [], next_id: 1 })) });
const dialog = page.locator('#import-dialog');
await dialog.waitFor({ state: 'visible' });
await page.waitForTimeout(80);
const initial = await page.evaluate(() => ({ open: document.querySelector('#import-dialog')?.open, inside: document.querySelector('#import-dialog')?.contains(document.activeElement), activeText: document.activeElement?.textContent?.trim() || '', labelled: Boolean(document.querySelector('#import-dialog')?.getAttribute('aria-labelledby')) }));
const focusableCount = await dialog.locator('button:not([disabled]):visible').count();
const tabTrace = [];
for (let i = 0; i < focusableCount + 1; i++) {
  await page.keyboard.press('Tab');
  tabTrace.push(await page.evaluate(() => ({ inside: document.querySelector('#import-dialog')?.contains(document.activeElement), activeId: document.activeElement?.id || '', activeText: document.activeElement?.textContent?.trim() || '' })));
}
await page.keyboard.press('Shift+Tab');
tabTrace.push(await page.evaluate(() => ({ inside: document.querySelector('#import-dialog')?.contains(document.activeElement), activeId: document.activeElement?.id || '', activeText: document.activeElement?.textContent?.trim() || '' })));
await page.screenshot({ path: `${out}/import-dialog-focus-v144.png`, fullPage: false });
await page.keyboard.press('Escape');
await page.waitForFunction(() => !document.querySelector('#import-dialog')?.open);
const afterEscape = await page.evaluate(() => ({ open: document.querySelector('#import-dialog')?.open, focusReturnedToImport: document.activeElement?.getAttribute('data-action') === 'import-json', activeText: document.activeElement?.textContent?.trim() || '' }));
const result = {
  date: '2026-11-05',
  build: 'v144 localhost app, isolated fresh Chromium context; no import strategy selected or data applied',
  httpStatus: response.status(),
  fixture: 'synthetic empty schema_version 1 JSON used for preview only',
  initial,
  tabTrace,
  afterEscape,
  runtimeErrors: errors,
  userDataChanged: false,
  passed: initial.open && initial.inside && initial.activeText === 'Отмена' && initial.labelled && tabTrace.every(step => step.inside) && !afterEscape.open && afterEscape.focusReturnedToImport && errors.length === 0,
};
await writeFile(`${out}/keyboard-import-v144-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# Клавиатурный проход диалога импорта — v144\n\nНа v144 проверены начальный фокус, Tab/Shift+Tab внутри диалога, Escape и возврат фокуса на действие импорта. Использован пустой синтетический JSON только для preview; решение импорта не выбиралось. Браузерный профиль изолирован, рабочие данные не затрагивались.\n\nСценарий: \`run-keyboard-import-v144.mjs\`; результат: \`keyboard-import-v144-results.json\`; кадр: \`import-dialog-focus-v144.png\`.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;
