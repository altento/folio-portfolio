# Web/PWA v74: safe replacement backup

QA covers the full-replacement import path in a clean isolated Chromium profile using only the bundled `web/demo.json` fixture. No user portfolio data was loaded or changed.

- `results.json` records browser state before and after both branches.
- `backup-failure-cancels-replace-with-notice.png` shows the import dialog and explicit cancellation message after `URL.createObjectURL` is forced to fail. IndexedDB revision and all three original project titles stayed unchanged.
- `replacement-success-backup-before-commit.png` shows the success message after the browser emitted `folio-before-import.json`; the replacement then committed successfully.
- Two additional viewport/full-page captures document the same failure branch.

Service Worker cache: `folio-shell-v74-safe-import-replace`.
