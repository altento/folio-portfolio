import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const css = readFileSync(new URL('../styles.css', import.meta.url), 'utf8');
const app = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

test('dashboard recommendation count is formatted once with Russian plural forms', () => {
  const helper = app.split(/\r?\n/).find(line => line.startsWith('function countLabel('));
  assert.ok(helper, 'countLabel must stay available to dashboard rendering');
  const countLabel = vm.runInNewContext(`(${helper})`);
  const forms = ['подсказка', 'подсказки', 'подсказок'];
  assert.equal(countLabel(1, forms), '1 подсказка');
  assert.equal(countLabel(3, forms), '3 подсказки');
  assert.equal(countLabel(5, forms), '5 подсказок');
  const badge = app.match(/<span class="insight-count">([\s\S]*?)<\/span>/)?.[1] ?? '';
  assert.match(badge, /recommendations\.length\?countLabel\(recommendations\.length,/);
  assert.doesNotMatch(badge, /recommendations\.length\}\s*\$\{countLabel/);
});

test('service-worker update notice separates its live message from its actions', () => {
  assert.match(html, /<div class="update-notice" id="update-notice" hidden role="region" aria-labelledby="update-notice-title">/);
  const status = html.match(/<p role="status" aria-live="polite" aria-atomic="true">[\s\S]*?<\/p>/)?.[0] ?? '';
  assert.ok(status, 'update copy must be announced politely as a status message');
  assert.match(status, /id="update-notice-title"/);
  assert.doesNotMatch(status, /<button\b/i, 'interactive update actions must stay outside the live status');
  assert.match(html, /<button[^>]*id="update-reload"/);
  assert.match(html, /<button[^>]*id="update-dismiss"/);
});

test('decorative button glyphs are hidden from assistive technology while controls keep clear names', () => {
  assert.match(html, /id="theme-toggle"[^>]*aria-label="Переключить тему"[^>]*>[\s\S]*?<svg[^>]*aria-hidden="true"[^>]*focusable="false"/);
  assert.match(html, /class="mobile-nav-item mobile-add"[^>]*aria-label="Добавить проект"><svg[^>]*aria-hidden="true"[^>]*focusable="false"/);
  assert.doesNotMatch(html, /<button[^>]*aria-label="[^"]+"[^>]*>×<\/button>/);
  assert.doesNotMatch(app, /<button[^>]*aria-label="[^"]+"[^>]*>×<\/button>/);
});

test('small white labels over project and dashboard artwork keep stable dark contrast backings', () => {
  assert.match(css, /\.hero-signature\{[^}]*background:#202126ee[^}]*text-shadow:none/);
  assert.match(css, /\.detail-shade\{background:linear-gradient\(90deg,#11130ff2 0%,#11130fe0 68%,#11130fd9 78%,#11130f15 100%\)\}/);
  const contrast = (foreground, background) => {
    const luminance = hex => {
      const channels = hex.slice(1).match(/.{2}/g).map(value => parseInt(value, 16) / 255);
      const linear = channels.map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
      return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2];
    };
    const a = luminance(foreground), b = luminance(background);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  };
  const compositedWorstCase = (overlay, opacity) => {
    const foreground = overlay.slice(1).match(/.{2}/g).map(value => parseInt(value, 16));
    const result = foreground.map(value => Math.round(value * opacity + 255 * (1 - opacity)));
    return `#${result.map(value => value.toString(16).padStart(2, '0')).join('')}`;
  };
  assert.ok(contrast('#ffffff', '#202126') >= 12, 'signature card text must stay readable against its solid backing');
  assert.ok(contrast('#ffffff', compositedWorstCase('#11130f', parseInt('d9', 16) / 255)) >= 4.5,
    'detail text must meet normal-text contrast over a worst-case white cover through the 78% stop');
});

function relativeLuminance(hex) {
  const channels = hex.slice(1).match(/.{2}/g).map(value => parseInt(value, 16) / 255);
  const linear = channels.map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

test('small sidebar labels and navigation counts meet WCAG AA contrast in both themes', () => {
  const foreground = css.match(/--sidebar-label\s*:\s*(#[\da-f]{6})/i)?.[1];
  const background = css.match(/\.sidebar\s*\{[^}]*background\s*:\s*(#[\da-f]{6})/i)?.[1];
  assert.ok(foreground, 'sidebar label contrast token must exist');
  assert.ok(background, 'sidebar background color must be explicit');
  assert.match(css, /\.workspace-label\s*,\s*\.nav-count\s*,\s*\.nav-external\s*\{\s*color\s*:\s*var\(--sidebar-label\)\s*\}/);
  const sidebarLuminance = relativeLuminance(background);
  const lightLuminance = relativeLuminance(foreground);
  const lightContrast = (Math.max(lightLuminance, sidebarLuminance) + 0.05) / (Math.min(lightLuminance, sidebarLuminance) + 0.05);
  assert.ok(lightContrast >= 4.5, `Light theme expected at least 4.5:1, got ${lightContrast.toFixed(2)}:1`);

  const darkRule = [...css.matchAll(/html\[data-theme=dark\][^{]*\{([^}]*)\}/g)]
    .find(match => match[0].includes('.workspace-label') && match[0].includes('.nav-count'));
  const darkForeground = darkRule?.[1].match(/color\s*:\s*(#[\da-f]{6})/i)?.[1];
  assert.ok(darkForeground, 'dark theme sidebar label color must be explicit');
  const darkLuminance = relativeLuminance(darkForeground);
  const darkContrast = (Math.max(darkLuminance, sidebarLuminance) + 0.05) / (Math.min(darkLuminance, sidebarLuminance) + 0.05);
  assert.ok(darkContrast >= 4.5, `Dark theme expected at least 4.5:1, got ${darkContrast.toFixed(2)}:1`);
});

test('dark-theme search shortcut and detail close control remain distinguishable', () => {
  assert.match(css, /html\[data-theme=dark\]\s+\.search-field\s+kbd\s*\{[^}]*color\s*:\s*#f0f0ed[^}]*background\s*:\s*#34353a/i);
  assert.match(css, /\.detail-hero\s+\.detail-close\s*\{[^}]*color\s*:\s*#25262a[^}]*background\s*:\s*#f5f5f3[^}]*border-color\s*:\s*#f5f5f3/i);
  const ratio = (foreground, background) => {
    const luminance = hex => {
      const channels = hex.slice(1).match(/.{2}/g).map(value => parseInt(value, 16) / 255);
      const linear = channels.map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
      return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2];
    };
    const a = luminance(foreground), b = luminance(background);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  };
  assert.ok(ratio('#f0f0ed', '#34353a') >= 4.5, 'dark search shortcut must meet normal-text contrast');
  assert.ok(ratio('#25262a', '#f5f5f3') >= 3, 'detail close glyph must meet non-text contrast');
});

test('mobile import dialog exposes a visible keyboard-focusable preview and separated action targets', () => {
  assert.match(html, /class="import-dialog-body" tabindex="0" role="region" aria-label="Предпросмотр импорта"/);
  assert.match(css, /\.import-dialog-body:focus-visible\s*\{[^}]*outline:3px solid #657c1f/i);
  assert.match(html, /class="icon-button import-dialog-cancel" data-close-dialog aria-label="Отмена"/);
  const actions = html.match(/<div class="import-actions">([\s\S]*?)<\/div>/)?.[1] ?? '';
  assert.equal((actions.match(/<button\b/g) || []).length, 3, 'the action footer exposes the three explicit import strategies');
  assert.match(css, /\.import-actions\s*\{[^}]*gap:24px/i);
  assert.match(css, /\.import-actions\{[^}]*display:grid[^}]*gap:24px/i, 'narrow layouts keep touch targets separated');
});

test('closed import dialog stays hidden on narrow screens', () => {
  assert.match(css, /@media\(max-width:820px\)\{\.import-dialog\[open\]\{display:flex;/,
    'mobile flex layout must apply only while the native dialog is open');
  assert.doesNotMatch(css, /@media\(max-width:820px\)\{\.import-dialog\{display:flex;/,
    'a closed dialog must not render at the end of the document');
});

test('forced-colors mode uses system colors for focus, dialogs and selected controls', () => {
  assert.match(css, /@media \(forced-colors: active\)/);
  assert.match(css, /:focus-visible \{ outline: 3px solid Highlight !important/);
  assert.match(css, /background: Highlight !important; color: HighlightText !important/);
  assert.match(css, /\.nav-item\.active span:not\(\[aria-hidden=\"true\"\]\) \{ forced-color-adjust: none !important; background-color: Highlight !important; color: HighlightText !important/);
  assert.match(css, /\.dialog, dialog \{ background: Canvas !important/);
  assert.match(css, /background: ButtonFace !important; color: ButtonText !important/);
});

test('replace import waits for a confirmed backup or explicit fallback confirmation', () => {
  assert.match(app, /async function saveReplacementBackup\(content\)/);
  assert.match(app, /window\.showSaveFilePicker/);
  assert.match(app, /return window\.confirm\('Браузер начал загрузку резервной копии/);
  assert.match(app, /if\(!backupSaved\)/);
  assert.match(html, /Если браузер не умеет подтвердить сохранение/);
});

test('favorite sorting is distinct from filtering to favorites', () => {
  assert.match(app, /option value="featured"[^>]*>Сначала избранные<\/option>/);
  assert.match(app, /option value="tags"[^>]*>По тегам<\/option>/);
  assert.match(app, /id="filter-featured"[^>]*> Только избранное<\/label>/);
});

test('closed mobile filter and saved-view disclosures keep their controls hidden', () => {
  assert.match(css, /\.project-filter-disclosure:not\(\[open\]\)\s*>\s*\.filter-disclosure-body,\s*\.saved-views-disclosure:not\(\[open\]\)\s*>\s*\.saved-views\s*\{\s*display:\s*none;\s*\}/);
});

test('mobile case editor keeps one form and exposes an accessible three-step flow', () => {
  assert.equal((html.match(/id="project-form"/g) || []).length, 1, 'all fields stay in the same form for draft restore and save');
  assert.match(html, /id="project-form-wizard"[^>]*aria-labelledby="project-form-step-title"/);
  assert.match(html, /id="project-form-wizard"[^>]*role="group"/);
  assert.match(html, /id="project-form-step-progress"[^>]*role="progressbar"[^>]*aria-valuemax="3"/);
  assert.match(html, /<label class="case-tag-entry-label" for="case-tag-entry">Добавить тег<\/label>/);
  assert.match(app, /case-tags-empty" role="listitem"/);
  assert.match(html, /id="project-form-step-back"[^>]*hidden/);
  assert.match(html, /id="project-form-step-next"[^>]*hidden/);
  assert.match(html, /type="submit"[^>]*id="project-form-submit"/);
  assert.match(app, /const projectFormSteps=\[\{title:/);
  assert.match(app, /function setProjectFormStep\(index,moveFocus=true\)/);
  assert.match(app, /window\.addEventListener\('resize',[\s\S]*requestAnimationFrame\([\s\S]*if\(visible\(focused\)\)return[\s\S]*#project-form-step-title/);
  assert.match(app, /function validateCurrentProjectStep\(\)/);
  assert.match(app, /scheduleProjectDraftSave\(\)/);
  assert.match(css, /@media\(max-width:820px\)\{/);
  assert.match(css, /@media\(max-width:820px\)\{\.project-dialog\[open\]\{display:flex/);
  assert.match(css, /\.project-dialog \[data-mobile-step-active="false"\]\{display:none!important\}/);
  assert.match(css, /\.project-form-step-copy h3:focus-visible\{outline:2px solid #829d29/);
  assert.match(html, /class="mobile-brand"[^>]*>[\s\S]*<svg aria-hidden="true"/);
});

test('mobile project wizard actions reflow on narrow phones without forcing fixed-width columns', () => {
  assert.match(css, /@media\(max-width:420px\)\{\s*\.project-dialog \.dialog-actions\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)\}/);
  assert.match(css, /\.project-dialog \.dialog-actions>\.button\{min-width:0;width:100%;padding-inline:8px;white-space:normal\}/);
  assert.match(css, /\.project-dialog #project-form-step-next,\.project-dialog #project-form-submit\{grid-column:1\/-1\}/);
});

test('desktop storage loss restores the durable local snapshot before considering the legacy database', () => {
  const recoveryRequest = app.indexOf("fetch('./desktop-recovery.json'");
  const legacyRequest = app.indexOf("fetch('./desktop-seed.json'");
  assert.ok(recoveryRequest >= 0 && legacyRequest > recoveryRequest, 'recovery snapshot must have priority over the old SQLite seed');
  assert.match(app, /recoveryResponse\.status!==204&&recoveryResponse\.status!==404/,
    'a broken recovery snapshot must fail closed instead of falling through to a stale legacy seed');
  assert.match(app, /save_recovery_snapshot/);
  assert.match(app, /desktopRecoveryMarkup\(\)/);
  assert.match(app, /backup-status desktop-recovery-status[^`]*role="status" aria-live="polite"/);
});

test('mobile project wizard keeps metadata in the final step and anchors actions outside the scroll area', () => {
  assert.match(app, /const projectMediaFields=new Set\(\['cover_image_data','gallery_images','page_count','repository_url','backend_stack','created_at','demo_url','technologies','tags','tag_draft'\]\)/);
  assert.match(app, /else if\(el\.matches\('\.featured-toggle'\)\)current=2/);
  assert.match(html, /<div class="project-form-scroll" id="project-form-scroll">/);
  assert.match(html, /<div class="project-form-scroll" id="project-form-scroll">\s*<div id="project-form-wizard"/);
  assert.match(css, /\.project-dialog \.project-form-scroll\{[^}]*overflow-y:auto/);
  assert.match(css, /\.project-dialog \.dialog-actions\{position:static;flex:0 0 auto/);
});

test('gallery caption is the single accessible description for each gallery image', () => {
  assert.match(app, /detail-gallery-item"><img src="\$\{esc\(image\.image_data\)\}" alt=""/);
  assert.match(app, /<figcaption>\$\{esc\(description\)\}<\/figcaption>/);
});

test('project cover labels keep strong contrast and stay out of the accessible card name', () => {
  assert.match(app, /class="cover-kicker" aria-hidden="true"/);
  assert.match(app, /class="cover-index" aria-hidden="true"/);
  assert.match(app, /selectable\?' project-card-selectable'/);
  assert.match(css, /\.project-cover \.cover-kicker,\.project-cover \.cover-index\{background:#202126;color:#fff;text-shadow:none;padding:5px 8px;border-radius:999px/);
  assert.match(css, /\.project-card-selectable \.cover-kicker\{left:64px;max-width:calc\(100% - 80px\)\}/);
  assert.match(css, /\.project-list \.project-card-selectable \.cover-kicker\{display:none\}/);
  const ratio = (foreground, background) => {
    const a = relativeLuminance(foreground), b = relativeLuminance(background);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  };
  assert.ok(ratio('#ffffff', '#202126') >= 4.5, 'cover labels must meet WCAG AA text contrast');
  assert.match(css, /@media\(max-width:480px\)\{\.project-list \.cover-kicker\{max-width:calc\(100% - 24px\);overflow:hidden;text-overflow:ellipsis/);
});

test('narrow-phone supporting copy keeps readable minimum sizes', () => {
  assert.match(css, /\.stat-card>span\{font-size:9px\}/);
  assert.match(css, /\.stat-card>small\{font-size:10px\}/);
  assert.match(css, /\.portfolio-insights \.insight-intro,[^{]+\{font-size:11px\}/);
  assert.match(css, /\.project-list \.card-description\{font-size:11px\}/);
  assert.match(css, /\.storage-meter-caption\{font-size:10px\}/);
  assert.match(css, /\.storage-reliability-note\{font-size:11px\}/);
  assert.match(css, /Final narrow-phone toolbar override:[\s\S]*?\.results-actions \.select-visible-control span\{font-size:11px/);
  assert.match(css, /Final narrow-phone toolbar override:[\s\S]*?\.results-actions \.view-toggle button\{[^}]*font-size:11px/);
});

test('mobile editorial labels and project tags keep a readable 10–11px floor', () => {
  assert.match(css, /Mobile readability: keep editorial labels compact while raising their floor\.[\s\S]*?@media\(max-width:720px\)\{\s*\.portfolio-insights \.eyebrow\{font-size:10px!important;letter-spacing:1px!important\}\s*\.portfolio-insights \.insight-count\{font-size:11px!important\}\s*\.editorial-stat-grid \.stat-card>span\{font-size:11px!important\}\s*\.project-card \.tag-row i\{font-size:11px!important\}\s*\}/);
});

test('short mobile viewports keep dashboard actions above fixed navigation', () => {
  assert.match(css, /@media\s*\(max-width:\s*820px\)\s*and\s*\(max-height:\s*560px\)\s*\{[\s\S]*?\.dashboard-hero-editorial \.hero-actions\s*\{\s*margin-top:\s*9px;\s*\}[\s\S]*?\.dashboard-hero-editorial \.dashboard-hero-art\s*\{\s*height:\s*56px;\s*min-height:\s*56px;\s*\}/);
  assert.match(css, /@media\s*\(max-width:\s*820px\)\s*and\s*\(max-height:\s*420px\)\s*\{[\s\S]*?\.dashboard-hero-editorial \.hero-actions\s*\{\s*margin-top:\s*6px;\s*\}[\s\S]*?\.dashboard-hero-editorial \.dashboard-hero-art\s*\{\s*display:\s*none;\s*\}/);
});

test('compact phone wizard reveals its first field and moves draft status after the form controls', () => {
  assert.match(css, /@media\(max-width:820px\) and \(max-height:650px\)\{[\s\S]*?#project-form-scroll\{display:flex;flex-direction:column\}[\s\S]*?\.project-form-scroll>\.form-grid\{order:1\}[\s\S]*?#project-draft-status\{order:4/);
  assert.match(app, /function validateCurrentProjectStep\(\)[\s\S]*?if\(invalid\)\{invalid\.reportValidity\(\);invalid\.focus\(\);return false\}/);
});

test('settings explain local data reset risk and recommend a portable backup', () => {
  assert.match(app, /Очистка данных приложения или сайта может удалить портфолио/);
  assert.match(app, /Регулярно сохраняйте JSON-копию вне приложения или браузерного профиля/);
});

test('settings explain cross-device JSON transfer and replacement impact', () => {
  assert.match(app, /class="transfer-steps"/);
  assert.match(app, /На старом устройстве скачайте JSON-копию портфолио/);
  assert.match(app, /На новом устройстве откройте folio и выберите/);
  assert.match(app, /Полная замена удалит текущие/);
  const dataInfo = app.match(/<div class="data-info">([\s\S]*?)<\/div>/)?.[1] ?? '';
  assert.match(dataInfo, /JSON-копия включает весь профиль/);
  assert.match(dataInfo, /скрытые на витрине контакты/);
  assert.match(dataInfo, /не шифрует данные отдельно от защиты устройства/);
});

test('static showcase preview avoids duplicate banner landmarks and preserves control contrast', () => {
  assert.match(html, /<div class="showcase-preview-header">/);
  assert.doesNotMatch(html, /<header class="showcase-preview-header">/);
  assert.match(css, /\.preview-size-button span\s*\{[^}]*opacity\s*:\s*1\s*;?\s*\}/);
});

test('profile conflict recovery does not turn the entire main landmark into a clickable Android target', () => {
  assert.match(app, /const profileLatest=e\.target\.closest\('\[data-profile-latest\]'\)/);
  assert.doesNotMatch(app, /main\.addEventListener\('click',[^;]*data-profile-latest/);
});

test('cover crop mode handling is scoped to its control group instead of the whole project form', () => {
  assert.match(app, /\$\('\.cover-editor-actions'\)\.addEventListener\('click',e=>\{const button=e\.target\.closest\('\[data-cover-crop-mode\]'\)/);
  assert.doesNotMatch(app, /\$\('#project-form'\)\.addEventListener\('click'/);
});
