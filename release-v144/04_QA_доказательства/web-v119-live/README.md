# Web v119 live smoke and dialog accessibility check

Date: 2026-11-05. Checked the published GitHub Pages app in an isolated Playwright context using installed Chrome. The page returned HTTP 200. The new-project form is a native modal `<dialog>`; Chromium accessibility tree reports role `dialog` and accessible name `Новый проект`. Focus enters the title field, Escape closes the dialog, and focus returns to the trigger. At 390 × 844 CSS pixels, the modal fits without internal or document horizontal overflow. No project data was submitted or changed.

Machine-readable evidence: `modal-results.json`. Screenshots in this directory capture desktop and phone-sized states. The earlier explicit Playwright role locator returned a false negative for this native dialog; the Chrome accessibility tree is the authoritative result.
