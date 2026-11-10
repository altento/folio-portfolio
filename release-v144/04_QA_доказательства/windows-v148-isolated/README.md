# Windows v148 isolated runtime smoke

A separate QA-specific onedir host was packaged from the same current `desktop_webview.py` and v148 web assets. Its wrapper uses port 41948 and a dedicated Temp profile. The user's existing `%LOCALAPPDATA%\Folio\portfolio_data.sqlite3` was not opened or modified.

The window opened successfully at 1426×933. UI Automation exposed the dashboard, local-storage status and three demo projects. The project catalog opened with three cards and search controls. Opening the first card showed its context, solution, process, role, outcome, tags and technology stack.

- `windows-v148-dashboard.png`
- `windows-v148-projects.png`
- `windows-v148-project-detail.png`
- `windows-v148-results.json`

Scope: this verifies the v148 desktop host source and web assets in a packaged Windows WebView2 shell. The release EXE with its normal profile was intentionally not launched because it targets the user's existing data. It is not a Narrator keyboard/speech acceptance test.

An end-to-end JSON import was started in the isolated profile, but the OS file-open dialog was exposed as a separate `msedgewebview2.exe` window that Computer Use could not target from the Folio window. No file was selected and no portfolio data changed. The isolated QA app was closed; the synthetic fixture was removed. The replace-backup logic is covered by the Web regression suite, but the native Windows file-picker flow remains unverified.
