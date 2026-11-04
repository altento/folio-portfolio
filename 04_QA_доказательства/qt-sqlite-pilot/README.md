
# Qt + SQLite pilot (exploratory QA)

This folder contains an isolated proof of concept for the existing desktop storage contract. It uses `SQLiteStore` from the project and creates only a synthetic database in Windows Temp. Each launch resets that synthetic database to its demo fixture. It never opens the portfolio's active database.

## Evidence

- `pyside_sqlite_pilot.py` — source for list, text search, accessible empty state, and create flow.
- `qt-sqlite-pilot-main.png` — two rows after the new project was saved and read back.
- `qt-sqlite-pilot-search-empty.png` — search result empty state.
- `qt-sqlite-pilot-results.json` — UI Automation and storage round-trip observations and limitations.

The pilot runs on Python 3.13.7 with PySide6-Essentials / Qt 6.12.0. In this environment PySide6 is in a temporary `site-packages` folder; it was not added to `requirements.txt` or the product launcher. The source locates the existing `sqlite_storage.py` when placed in the root QA folder or in the submission package. The runtime has to have the stated Qt dependency available.

This is not a product migration or screen-reader acceptance. It does not yet implement edit, delete, galleries, profile, import/export, or full parity with Tkinter. The UI Automation report also showed a lagging focused-element value after Tab even though the screenshot showed the caret in the description field; this needs a real NVDA/Narrator pass.
