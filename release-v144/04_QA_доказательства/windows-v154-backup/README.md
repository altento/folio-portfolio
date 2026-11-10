# Windows WebView2 v154 — JSON backup export

- Fresh isolated profile: `%TEMP%/folio-desktop-v154-backup-qa`; user profile untouched.
- JSON export redirected by `FOLIO_EXPORT_DIR` to the isolated QA folder; real Downloads not touched.
- `folio-backup.json`: 4,896 bytes, schema 1, three sample projects, UTF-8 parse succeeds.
- A second export was saved under a unique suffixed name; the earlier backup was preserved.
- After restart with the same profile and loopback port, the UI showed “Копия соответствует текущим данным”.
- Screenshot: `backup-export-confirmed.jpg`; measurements and SHA-256 values: `result.json`.
- Windows native import file picker remains unverified.
