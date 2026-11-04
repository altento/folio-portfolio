# Android v92 cold offline check

Debug APK SHA-256: `7984090366a320cbbadd2466204170ab60ecc0063a1872e5a07ac71092793a99`.

On the isolated Android API 36 AVD `FolioQA_API36`, installation succeeded. With airplane mode enabled, the app was force-stopped and relaunched. The launcher returned to `ru.folio.portfolio/.MainActivity`; the attached WebView was `https://localhost/`, controlled by the Service Worker, and rendered the Projects view with three demo cases. CSS viewport and document width both measured 412 px. The mobile toolbar labels measured 12/11/12 px. The screenshots show the settled dashboard and the projects view while offline.

Machine results: `results.json`. WebView measurements: `verify-android.mjs`. The AVD is not a physical phone; screenreader and zoom remain untested.
