import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const css = readFileSync(new URL('../styles.css', import.meta.url), 'utf8');
const app = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

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

test('favorite sorting is distinct from filtering to favorites', () => {
  assert.match(app, /option value="featured"[^>]*>Сначала избранные<\/option>/);
  assert.match(app, /id="filter-featured"[^>]*> Только избранное<\/label>/);
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
  assert.match(css, /\.project-dialog \[data-mobile-step-active="false"\]\{display:none!important\}/);
  assert.match(css, /\.project-form-step-copy h3:focus-visible\{outline:2px solid #829d29/);
  assert.match(html, /class="mobile-brand"[^>]*>[\s\S]*<svg aria-hidden="true"/);
});

test('gallery caption is the single accessible description for each gallery image', () => {
  assert.match(app, /detail-gallery-item"><img src="\$\{esc\(image\.image_data\)\}" alt=""/);
  assert.match(app, /<figcaption>\$\{esc\(description\)\}<\/figcaption>/);
});

test('narrow-phone supporting copy keeps readable minimum sizes', () => {
  assert.match(css, /\.stat-card>span\{font-size:9px\}/);
  assert.match(css, /\.stat-card>small\{font-size:10px\}/);
  assert.match(css, /\.portfolio-insights \.insight-intro,[^{]+\{font-size:11px\}/);
  assert.match(css, /\.project-list \.card-description\{font-size:11px\}/);
  assert.match(css, /\.storage-meter-caption\{font-size:10px\}/);
  assert.match(css, /\.storage-reliability-note\{font-size:11px\}/);
});

test('settings explain private browsing data loss and recommend a portable backup', () => {
  assert.match(app, /В приватном режиме данные могут удалиться после закрытия сеанса/);
  assert.match(app, /Для постоянного хранения используйте обычный профиль/);
  assert.match(app, /регулярно сохраняйте JSON-копию вне профиля/);
});

test('settings explain cross-device JSON transfer and replacement impact', () => {
  assert.match(app, /class="transfer-steps"/);
  assert.match(app, /На старом устройстве скачайте JSON-копию портфолио/);
  assert.match(app, /На новом устройстве откройте folio и выберите/);
  assert.match(app, /Полная замена удалит текущие/);
});

test('static showcase preview avoids duplicate banner landmarks and preserves control contrast', () => {
  assert.match(html, /<div class="showcase-preview-header">/);
  assert.doesNotMatch(html, /<header class="showcase-preview-header">/);
  assert.match(css, /\.preview-size-button span\s*\{[^}]*opacity\s*:\s*1\s*;?\s*\}/);
});
