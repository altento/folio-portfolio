# Mobile closed-dialog regression — Web/PWA v149

At 320×568 CSS px, an import dialog that is closed must not appear as a flex box at the end of the document. Before the fix its box was 289×445.5 px and inflated the document height from 3236 to 3682 px. With `.import-dialog[open]`, the closed dialog computes to `display:none`, has a zero-size rectangle, and no longer inflates the page. A separately opened modal remains fixed, 289×445.5 px, and fits inside the viewport. The browser test used an isolated context and synthetic demo content; no user data was touched.

The CSS regression is covered by the Web suite: 70 tests passed, 0 failed. Screenshot capture is unavailable through the isolated browser bridge, so the evidence is recorded as DOM/CSS measurements.
