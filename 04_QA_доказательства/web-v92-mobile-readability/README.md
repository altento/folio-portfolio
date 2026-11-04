# Web/PWA v92: readability at narrow widths

Checked the local app in a fresh headless Chrome profile over Chrome DevTools Protocol. This avoids the user browser profile and does not change its tabs or local data. The app was opened to «Мои проекты» and captured at 320×900 and 390×900 CSS px.

In both captures, `document.documentElement.scrollWidth` equals the CSS viewport width. The selection label measures 12 px, layout buttons 11 px, filter reset 12 px. Control heights are 44–52 px. Service Worker v92 controlled both pages. Full computed values are in `results.json`; `capture.mjs` reproduces the check.

This confirms Chromium responsive layout only. It does not replace a physical phone, screenreader, or 200% zoom acceptance. The Playwright MCP snapshot call failed with ENOENT; the Chromium CDP smoke provided the viewport and screenshots.
