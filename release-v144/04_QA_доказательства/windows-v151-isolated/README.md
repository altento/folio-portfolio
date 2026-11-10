# Windows WebView2 v151 isolated launch

Date: 2026-11-07. The exact packaged executable `dist/folio-webview-v151/folio-desktop/folio-desktop.exe` was launched in a dedicated temporary profile at `%TEMP%/folio-desktop-v151-final-qa`, on isolated loopback port 41765. The existing v150 process and user profile were not used or stopped.

## Observed

- The app opened the dashboard and rendered its hero artwork and three demo project cards without a startup error.
- The dashboard showed 3 projects after a full WebView reload.
- The Projects route opened and showed 3 project cards, search, type/status/tag filters, sorting, saved views, and card/list mode controls.
- Settings opened. The JSON backup section was visible and honestly showed “Резервная копия не отмечена”; no export or import was initiated.
- A separate synthetic CRUD pass used only this Temp profile: adding one QA case changed the catalog count 3→4; a full WebView reload retained it; the case details opened; editing its description was reflected in the project card; deleting the selected case displayed the app's 7-second undo notice; the notice expired and the catalog returned to the original 3 demo cases.
- Screenshots are 1426×933 JPEGs: dashboard, project catalog, and backup settings. They are current GUI captures from the v151 executable.
- Two additional JPEG frames show the synthetic case in the catalog and the clean 3-demo state after deletion. `portfolio_data.sqlite3` in the isolated profile remains 0 bytes with no tables; the tested app data is isolated in the temporary WebView2 profile under the same Temp directory.

## Limits

The synthetic CRUD pass proves create, reload persistence, detail view, edit persistence, and recoverable delete on the exact Windows v151 executable in its dedicated Temp profile. Native file picker, Windows Narrator, system zoom, JSON export/import, and physical-device behavior remain unverified.

Executable SHA-256: `1bb9dedec6bdb8a2baeeea1c631d0cd49a53661736fe081f58804347a1ad41ba`

Screenshot SHA-256:

- `folio-v151-dashboard-1426x933.jpg`: `3122b737228930acc6654e3ad91044635c59ca19345938e2d7e51d711c19f66d`
- `folio-v151-projects-1426x933.jpg`: `206804b08da35e4f5441e6a37c55f9fd617fa3df2d6db18af12aef66b230bdef`
- `folio-v151-settings-backup-1426x933.jpg`: `2e460e55af8653cf886606b9da852087c0447d7cfccef21985542050ab7fb436`
- `folio-v151-crud-created-1426x933.jpg`: `cc8d7039e18d839564b51bc54b1a0a82320f07cd70f95814a89d884b514e3093`
- `folio-v151-crud-clean-1426x933.jpg`: `348daac7ff7da3416b5adfc89a79ff95dff8737dfdfea83e515d0f3b0eb4ada0`
