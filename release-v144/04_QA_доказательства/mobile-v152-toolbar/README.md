# Mobile toolbar readability — Web/PWA v152

Date: 2026-11-07

Run: `python run_mobile_toolbar_readability_v152.py`

The smoke used a new isolated Playwright browser context against the local Web/PWA. It checked viewports 390×568, 390×844, 320×568, and 1440×900 CSS px. There was no horizontal overflow. At narrow phone widths, the selection label, view toggle, and reset text measured 11 px; touch controls measured at least 44 px. Searching for CRM returned one case; Reset restored the empty query and all three demo projects. HTTP status was 200 and browser page/console errors were zero.

Evidence: `result.json`, `mobile-toolbar-390x568.png` (SHA-256 `3313345adf96bcc08143d833df9b7f8d128016b4959f6395c1eae1ff8c844c47`). No real phone was used.
