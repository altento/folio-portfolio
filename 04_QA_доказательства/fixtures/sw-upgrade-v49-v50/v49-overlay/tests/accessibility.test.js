import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const css = readFileSync(new URL('../styles.css', import.meta.url), 'utf8');

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
