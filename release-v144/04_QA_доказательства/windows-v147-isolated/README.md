# Windows v147 packaged smoke

Launched the exact `dist/folio-webview-v147/folio-desktop/folio-desktop.exe` with `--profile-dir` set to a dedicated Temp folder and port 41947. The native WebView2 window opened, the dashboard displayed three demo projects, and the Windows accessibility tree exposed the page structure and project count. The user's normal Folio profile was not opened.

- Screenshot: `windows-v147-isolated-home.png`
- Structured result: `windows-v147-isolated-results.json`
- This is a smoke check of startup, rendering, and the exposed UI tree; it is not a Narrator speech/keyboard acceptance run.
