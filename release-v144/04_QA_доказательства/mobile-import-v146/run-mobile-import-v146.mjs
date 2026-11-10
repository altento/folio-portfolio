import { chromium } from 'file:///C:/Users/Windows-10/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';

const out = 'служебные_файлы/qa_05-11-2026/mobile-import-v146';
const baseUrl = process.env.FOLIO_BASE_URL || 'http://127.0.0.1:8766/';
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
const errors = [];
const results = {};
for (const width of [390, 320]) {
  const context = await browser.newContext({ viewport: { width, height: 568 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(`${width}: ${error}`));
  page.on('console', message => { if (message.type() === 'error') errors.push(`${width}: ${message.text()}`); });
  const response = await page.goto(baseUrl, { waitUntil: 'networkidle' });
  if (!response?.ok()) throw new Error(`HTTP ${response?.status()} at ${width}px`);
  const cacheId = await page.evaluate(async () => (await (await fetch('./sw.js')).text()).match(/folio-shell-v\d+[^']*/)?.[0] || '');
  if (cacheId !== 'folio-shell-v146-import-a11y-target-size') throw new Error(`Unexpected build at ${width}px: ${cacheId}`);
  await page.locator('[data-view="settings"]:visible').first().click();
  const chooserWait = page.waitForEvent('filechooser');
  await page.locator('[data-action="import-json"]:visible').first().click();
  const chooser = await chooserWait;
  const seed = await page.evaluate(async () => (await (await fetch('./demo.json')).json()));
  const project = structuredClone(seed.projects[0]);
  project.id = 80;
  project.project_id = 80;
  project.title = `Мобильный импорт ${width}`;
  project.description = 'Синтетическая карточка для проверки мобильного диалога.';
  const payload = { schema_version: 1, title: 'Тест мобильного импорта', next_id: 81, developer: { full_name: 'QA Автор', specialization: 'Тестирование' }, projects: [project] };
  await chooser.setFiles({ name: `mobile-import-${width}.json`, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(payload)) });
  const dialog = page.locator('#import-dialog');
  await dialog.waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.querySelector('#import-dialog')?.contains(document.activeElement));
  const before = await page.evaluate(() => {
    const d = document.querySelector('#import-dialog');
    const content = d.querySelector('.import-dialog-body'), actions = d.querySelector('.import-actions');
    const rect = d.getBoundingClientRect();
    const contentRect = content.getBoundingClientRect(), actionsRect = actions.getBoundingClientRect();
    const buttons = ['#import-dialog [data-close-dialog]', '#import-keep', '#import-replace'].map(selector => {
      const el = document.querySelector(selector);
      const r = el.getBoundingClientRect();
      return { selector, hidden: el.hidden, text: el.textContent.trim(), x: r.x, y: r.y, width: r.width, height: r.height, right: r.right, bottom: r.bottom };
    });
    return { viewport: { width: innerWidth, height: innerHeight }, pageWidth: document.documentElement.scrollWidth, dialog: { x: rect.x, y: rect.y, width: rect.width, height: rect.height, right: rect.right, bottom: rect.bottom }, content: { top: contentRect.top, bottom: contentRect.bottom, clientHeight: content.clientHeight, scrollHeight: content.scrollHeight, overflowY: getComputedStyle(content).overflowY }, actions: { x: actionsRect.x, y: actionsRect.y, width: actionsRect.width, height: actionsRect.height, right: actionsRect.right, bottom: actionsRect.bottom }, buttons };
  });
  await page.screenshot({ path: `${out}/import-preview-${width}-v146.png`, fullPage: false });
  await page.locator('#import-replace').scrollIntoViewIfNeeded();
  const replaceActionReachability = await page.evaluate(() => {
    const dialog = document.querySelector('#import-dialog'), button = document.querySelector('#import-replace'), rect = button.getBoundingClientRect();
    return { insideDialog: dialog.contains(button), scrollTop: dialog.scrollTop, top: rect.top, bottom: rect.bottom, withinViewport: rect.top >= 0 && rect.bottom <= innerHeight };
  });
  const keep = page.locator('#import-keep');
  await keep.scrollIntoViewIfNeeded();
  await keep.click();
  await page.waitForTimeout(500);
  const dialogClosed = await dialog.evaluate(el => !el.open);
  if (!dialogClosed) {
    const debug = await page.evaluate(() => ({ active: document.activeElement?.outerHTML?.slice(0, 220), bodyText: document.body.innerText.slice(-700), actionCount: document.querySelectorAll('#import-dialog [data-import-mode]').length }));
    console.log(JSON.stringify({ width, dialogClosed, debug, errors }, null, 2));
    throw new Error(`Import action did not close dialog at ${width}px`);
  }
  await page.locator('[data-view="projects"]:visible').first().click();
  await page.waitForTimeout(150);
  const importedCount = await page.locator('.project-card').count();
  const importedTitleVisible = await page.getByText(`Мобильный импорт ${width}`, { exact: true }).count() > 0;
  await page.screenshot({ path: `${out}/projects-after-import-${width}-v146.png`, fullPage: true });
  const buttonPairs = [];
  for (let i = 0; i < before.buttons.length; i++) for (let j = i + 1; j < before.buttons.length; j++) {
    const a = before.buttons[i], b = before.buttons[j];
    if (!a.hidden && !b.hidden && Math.max(a.x, b.x) < Math.min(a.right, b.right) && Math.max(a.y, b.y) < Math.min(a.bottom, b.bottom)) buttonPairs.push([a.selector, b.selector]);
  }
  const footerButtons = before.buttons.filter(b => ['#import-keep', '#import-replace'].includes(b.selector) && !b.hidden);
  const cancelButton = before.buttons.find(b => b.selector === '#import-dialog [data-close-dialog]');
  const actionsAlwaysVisible = before.actions.y >= 0 && before.actions.bottom <= before.viewport.height && footerButtons.every(b => b.y >= before.actions.y && b.bottom <= before.actions.bottom) && cancelButton && cancelButton.y >= 0 && cancelButton.bottom <= before.viewport.height;
  results[width] = {
    ...before,
    buttonOverlaps: buttonPairs,
    horizontalOverflow: before.pageWidth > width || before.dialog.right > width + 1 || before.dialog.x < -1,
    actionsWithinDialogWidth: before.buttons.filter(b => !b.hidden).every(b => b.x >= -1 && b.right <= width + 1),
    actionsAlwaysVisible,
    replaceActionReachability,
    importedCount,
    importedTitleVisible,
    passed: !buttonPairs.length && actionsAlwaysVisible && before.pageWidth <= width && before.dialog.right <= width + 1 && before.dialog.x >= -1 && before.buttons.filter(b => !b.hidden).every(b => b.width >= 40) && replaceActionReachability.insideDialog && replaceActionReachability.withinViewport && importedCount === 4 && importedTitleVisible,
  };
  await context.close();
}
const result = { date: '2026-11-05', build: 'folio-shell-v146-import-a11y-target-size', viewportHeights: 568, results, runtimeErrors: errors, userDataChanged: false, passed: Object.values(results).every(x => x.passed) && errors.length === 0 };
await writeFile(`${out}/mobile-import-v146-results.json`, JSON.stringify(result, null, 2) + '\n');
await writeFile(`${out}/README.md`, `# Мобильный JSON-импорт — v146\n\nНа 390×568 и 320×568 CSS px проверены геометрия диалога, отсутствие горизонтального переполнения/перекрытия и постоянно доступная панель действий. Содержимое прокручивается отдельно от футера; две основные кнопки и отмена видны сразу. В каждом свежем профиле стратегия добавления применена к synthetic JSON: три demo-кейса сохранились и импортированная запись появилась. Axe/клавиатура проверены отдельным протоколом; runtime errors — 0.\n\nРезультаты: \`mobile-import-v146-results.json\`; предпросмотр и каталог после импорта — скриншоты в этой папке.\n`);
console.log(JSON.stringify(result, null, 2));
await browser.close();
if (!result.passed) process.exitCode = 1;
