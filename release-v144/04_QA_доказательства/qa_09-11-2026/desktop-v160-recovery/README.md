# Windows v160 local recovery check

Date: 10 November 2026. This check exercised the first-run recovery path served by the exact local Windows WebView2 v160 host at `127.0.0.1:41800`.

The test used a fresh, isolated Chrome context with no existing IndexedDB database. A synthetic fourth project was placed in the temporary recovery snapshot; all four projects, including the marker `QA: восстановленный проект`, appeared in the app after the recovery endpoint loaded. The page returned HTTP 200 and recorded no page or console errors. A minimal `pywebview` callback stub acknowledged the snapshot-save call so the recovery confirmation could be captured. The original temporary recovery file was restored byte-for-byte after the run.

This verifies the browser recovery flow against the v160 host and uses no personal browser profile or working database. The stub is not the native WebView2 bridge, and this check does not claim a full native-window UI test or a destructive wipe of WebView2 storage.

- Repeatable runner: `run_recovery_flow.py`
- Machine-readable result: `result.json`
- Full-page screenshot: `recovered-projects-v160-1440x900.png`
