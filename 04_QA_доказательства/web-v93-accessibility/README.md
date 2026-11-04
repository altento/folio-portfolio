# Web/PWA v93 accessibility regression

Audited the current local build at `http://127.0.0.1:8766/` after the v93 storage-resilience change.

- axe-core 4.14.0 scanned 12 states across dashboard, case details, projects, showcase, settings, mobile and desktop, in light and dark themes. Selected WCAG 2.2 AA and best-practice rules reported **0 violations**.
- Keyboard/name/label smoke covered 8 views, the new-project modal, required-field feedback, reduced motion and 320/390/1440 CSS px layouts. **PASS**, no page or console errors.
- Machine-readable results: `axe-a11y-results-v93.json`, `a11y-keyboard-results.json`.
- Representative screenshots: mobile dashboard, mobile new-project dialog, desktop projects, dark desktop dashboard, and compact settings.

This is an automated subset of accessibility checks. It does not claim complete WCAG conformance and does not replace a real screen-reader pass, magnification testing or physical-device review.
