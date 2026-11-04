# Browser reflow and zoom-equivalent sample — 02.11.2026

Read-only check in isolated Playwright context `folio-zoom-audit` against `http://127.0.0.1:8766/`. The CSS viewport was set to 320×800 and 720×900 to sample narrow reflow corresponding to 400% and 200% browser zoom on typical desktop widths. This is a viewport simulation, not direct browser zoom or operating-system text scaling.

## Results

- Projects/catalog at 320 CSS px: document width 305 CSS px (client width 305); no horizontal overflow.
- Add-project dialog at 320 CSS px: 304×736 px; 2,549 px content height scrolls vertically, 289 px content width with no horizontal overflow. Visible text fields and main actions are at least 44 px high.
- Phone HTML preview at 320 CSS px: outer width 305 px; iframe content width and scroll width both 288 px; no horizontal overflow. The preview scrolls vertically.
- Projects/catalog at 720 CSS px: document width 705 px; no horizontal overflow or visible focusable controls outside the viewport.
- Selection checkbox labels provide at least 44×44 px hit areas despite the smaller drawn checkbox glyph.

The isolated run uses demonstration records and did not modify application data. It does not close the remaining accessibility checks: actual zoom/system scaling in a browser, a complete all-views reflow pass, screen-reader announcements, manual color contrast, Android TalkBack, and physical-device review.

## Evidence

- `projects-zoom-400-effective-320x800.jpg`
- `showcase-preview-320x800.png`
- `projects-zoom-200-effective-720x900.jpg`
- `results.json` includes viewport measurements and SHA-256 values.
