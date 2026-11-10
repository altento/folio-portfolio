# Safe replace E2E — Web/PWA v148

Scope: isolated Chromium only, using a synthetic transfer JSON and the actual v148 application code. The browser's `showSaveFilePicker` was stubbed to capture the file contents and simulate the writable handle; no user profile or real local portfolio was touched.

## Results

1. The app loaded the three demo projects into the isolated IndexedDB store `folio-workspace/portfolio`.
2. A one-project synthetic JSON was uploaded with Playwright. Preview correctly showed 1 incoming, 3 current, 0 ID conflicts, and warned that replacement deletes the current 3.
3. The fake save picker rejected with `AbortError`. The app cancelled replacement, kept the preview open, and the stored portfolio still contained the same 3 project titles.
4. The picker then returned a writable handle. The test captured the backup JSON and the writer's `close()` completion. Instrumented IndexedDB writes confirmed the backup was closed before the replacement transaction wrote its one-project value.
5. The final portfolio contained only `QA synthetic transfer case`; a page reload retained that one record.

Screenshots: `01-preview.png`, `02-cancelled.png`, `03-replaced.png`, and `04-persisted-after-reload.png`. Structured values and write-order evidence are in `results.json`.

Limit: this proves app behavior around the File System Access picker contract, but does not prove the operating system's actual save dialog. The native file chooser is still an external manual gate.
