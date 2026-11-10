# Browser JSON import and restore QA

- Source: local Folio `web/` served on an ephemeral loopback port.
- Browser: isolated headless Chrome context, 1440×1000 viewport; no user browser profile or production data.
- Input: `input-synthetic.json`, one synthetic project with a unique ID.
- Preview: one incoming project, three existing projects, zero conflicting IDs.
- Replace flow: app downloaded `replacement-backup-before-import.json` (three existing demo projects) before full replacement; the isolated test accepted the app confirmation.
- Result: catalog contained one synthetic project before and after reload; browser console errors and page errors were both zero.
- Screenshots: `import-preview.png`, `import-complete.png`, and `import-complete-after-reload.png`.
- The file was assigned with Playwright `set_input_files`; this validates shared import logic and IndexedDB persistence, not the native Windows file picker.
- `result.json` contains machine-readable outcomes. SHA-256 values for all files were checked locally and are recorded in the parent QA report where relevant.
- Mobile browser preview at 390×844 CSS px fit the viewport with no horizontal overflow; close/cancel retained all three source projects. Visible buttons measured 44 and 46 px. Evidence: `mobile-import-preview-390x844.png` and `mobile-preview-result.json`.
