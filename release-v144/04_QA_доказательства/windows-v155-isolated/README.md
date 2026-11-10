# Windows WebView2 v155 — isolated runtime smoke (07.11.2026)

## Setup

- Binary: `dist/folio-webview-v155/folio-desktop/folio-desktop.exe`, SHA-256 `E4498C77E7C989047DFE287A8E29CD50FE7AFA0A8340D933C3E87F90105F85A2`.
- Launched as the v155 onedir executable using the application's explicit `--profile-dir` option and loopback port `41765`.
- Profile was a fresh, unique directory under Windows `%TEMP%` (`folio-desktop-v155-qa-<random>`); it contained only app-seeded demonstration data. The user's normal profile and database were not opened or modified.
- Native Windows window title: `folio — личное портфолио`; embedded document origin: `http://127.0.0.1:41765/`.

## Checks performed

1. The packaged app launched in a native WebView2 window and rendered the dashboard with its hero illustration and 3 demonstration projects.
2. Navigated to the project catalog. Search for `CRM` returned one matching project; resetting the demo data returned the catalog to 3 examples. The final catalog/reset screen is captured in `v155-catalog-reset.jpg`.
3. Navigated to Settings and Data. Profile form, local-storage explanation, backup/export/import controls, storage section, and application information were visible. No export, import, delete-all, or profile-save operation was invoked.
4. Navigated back to the dashboard; all 3 examples remained present. The settings and dashboard screens are captured separately.

## Evidence

| File | SHA-256 |
| --- | --- |
| `v155-dashboard.jpg` | `4F5AB6305EE43802BB57730885D6FCE0D89578E2269252BC46BAC0A6B8B8FB25` |
| `v155-catalog-reset.jpg` | `8F6FF782926BCB9505D93BEB80EFF29F54CBB11FA6D74A874F706B39ED7B50BE` |
| `v155-settings.jpg` | `B9C4AA9F784510CCE02B95122C54484EE1581D064FA0D608742E5D104222C67D` |

## Limits

This is a focused packaged-runtime smoke, not a full Windows acceptance run. Native JSON file-picker/import and JSON export were verified separately against v154; they were not repeated against v155. This pass did not cover the complete CRUD workflow, Narrator speech/gestures, Windows Magnifier/system zoom, or physical-device acceptance.
