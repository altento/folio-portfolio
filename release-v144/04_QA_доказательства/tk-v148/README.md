# Isolated Windows Tk QA — 2026-11-06

## Scope and safety

The current `main.py` and rebuilt Windows fallback executable `folio.exe` were opened with an isolated profile under `tmp/qa-tk-exe-v148-profile/Folio/portfolio_data.sqlite3`. It contained only the three built-in demo cases. The user's normal `%LOCALAPPDATA%\Folio` database was not opened. The add form was inspected and cancelled without saving.

## Results

- Tk 8.6 rendered the editorial dashboard, project cards, covers, search/filter controls, and fixed action bar.
- Keyboard Tab moved from the hero action to search. In the add form, initial focus was on the required title; Tab moved to the description with a visible lime focus outline.
- Mouse wheel moved the tall add form down to lower fields while Cancel and Save stayed visible. After cancelling, the isolated SQLite database still contained three projects.
- The project viewer showed structured case details and its cover gallery. On the original source run the viewer appeared at the top-left. Added `center_window_position`, centered this dialog, and made it resizable. In the rebuilt `folio.exe`, the captured viewer bounds were origin (447, 190), size 1042×732. Escape closes it and returns focus to the Card action.
- Windows UI Automation exposes the Tk client mostly as unnamed panels. This visual/keyboard smoke is not represented as Narrator or screen-reader acceptance.

## Captures

- `01-overview.jpg` — isolated source run.
- `02-add-form.jpg` — add form and initial title focus.
- `03-scrolled-form.jpg` — lower fields after wheel scroll; fixed actions remain visible.
- `04-project-detail.jpg` — original pre-fix top-left detail viewer.
- `05-exe-overview.jpg` — rebuilt fallback executable.
- `06-centered-detail.jpg` — centered viewer in rebuilt executable.

No test case was saved or deleted. Long-form detail overflow, Narrator speech/gestures, and other display scales remain unverified.
