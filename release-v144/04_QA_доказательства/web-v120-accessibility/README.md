# Axe accessibility check — local Web/PWA v120

The local app build is scanned in an isolated Playwright browser context with pinned axe-core 4.14.0. It covers dashboard, projects, detail, all three mobile editor steps, light/dark settings and desktop/mobile showcase preview. Screenshots and machine-readable results are written beside the script. The editor values are temporary and unsaved.

Axe is an automated subset check; review `incomplete_review_targets` in results for items requiring manual contrast/semantics inspection. It is not WCAG certification and does not replace real assistive technology testing.
`github-pages-live-v120-smoke.json` records a post-publish smoke check of the public Pages build.


## Public v120 route matrix

un_public_cross_route_v120.py opens the published Pages build in isolated Chrome and captures dashboard, projects, showcase and settings at 1440×900 and 390×844. esults-v120.json records document dimensions, image decoding, hidden decorative labels, console/page errors and overflow; eight full-page screenshots are saved next to this file. The check does not edit or import data.
