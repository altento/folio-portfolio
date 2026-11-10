# JSON backup and import check — v151b

Date: 2026-11-06. Target: isolated Playwright profile at `http://127.0.0.1:8777/`; no user browser profile or local Windows database used.

## Results

- Export produced `folio-backup.json`, MIME `application/json`, 4,896 bytes. It parsed as JSON and contained `schema_version`, `title`, `next_id`, `developer`, and `projects`; three projects were present.
- Declining the app's “download completed” confirmation left the backup status at “Резервная копия не отмечена”. This is the expected truthful state.
- Import preview recognized all three existing IDs as matches, zero new records, and warned that replacement would remove the current three records.
- Chose “Объединить, оставить мои совпадения”. The preview closed; IndexedDB `folio-workspace` record `portfolio` still had three projects, IDs 1–3, with the original titles. The sidebar still showed 3 after apply.
- The test file was injected as a synthetic browser `File` from the captured export content. This verifies app parsing, preview, and merge behavior; it does not verify the native OS file picker.
- The full-replacement path was not exercised. The test never confirmed an external backup download.

## Scope

Isolated synthetic test only. User data and the Windows EXE were untouched. Browser storage reported one portfolio record and three projects after merging matching IDs. The test supports JSON export/import within the browser flow; it does not establish cross-device transfer on a physical phone.
