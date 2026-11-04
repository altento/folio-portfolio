# Web/PWA v93: start with blocked localStorage

**Change under test:** `app.js` uses `preferences.js` for optional browser preferences. The adapter catches a blocked `window.localStorage` accessor and keeps preferences in memory for the current session.

**Automated checks:** `npm test` — 31/31. `node --check app.js core.js preferences.js sw.js` — passed. `verify-localstorage-blocked.mjs` starts a fresh headless Chrome profile, injects a getter that throws `SecurityError` before app scripts run, and checks the rendered dashboard and demo cards.

**Observed:** heading `Ваши проекты, собранные в одном месте.`, 3 project cards, no fatal state. Screenshot: `web-v93-dashboard-localstorage-blocked.png`; machine-readable result: `results.json`.

This verifies only optional preference storage failure. It does not simulate IndexedDB denial, quota exhaustion, screen-reader behavior, or mobile hardware.
