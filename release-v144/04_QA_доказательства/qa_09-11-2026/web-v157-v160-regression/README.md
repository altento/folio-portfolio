# Web/PWA v157 through Windows WebView2 v160 host

Date: 9 November 2026. The exact local host launched from `dist/folio-webview-v160/folio-desktop/folio-desktop.exe` served the current Web/PWA v157 files on loopback port 41800. Browser checks ran in an isolated installed-Chrome/Playwright context; the personal Chrome profile and working app data were not used.

The responsive matrix covered dashboard, projects, showcase and settings at 320×568, 390×568, 390×844, 768×900 and 1440×900: 20/20 route/viewport states passed. Horizontal overflow, broken project images, browser errors and visible touch targets shorter than 44 CSS px were all 0. A cold offline reload retained the app, three demo projects and images. The synthetic CRUD flow created a project, verified persistence after reload, edited it, used Undo after deletion and confirmed permanent deletion after the recovery period; the final demo count returned to three.

This is browser verification against the exact Windows host resources. It does not claim full pointer/keyboard interaction with the native WebView2 window or real-device mobile acceptance.

- Repeatable runner: `run_product_flow_v157_v160.py`
- Machine-readable protocol: `result.json`
- Screenshots: dashboard, projects, settings and offline states at mobile and desktop sizes
