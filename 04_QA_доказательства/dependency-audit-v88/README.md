# Android build dependency audit — 01.11.2026

The full `npm audit` initially found four moderate advisories in the Android build-only chain `@capacitor/cli@8.6.0 → rimraf@6.1.3 → glob@13.0.6 → minimatch@10.2.6`. Production dependencies were already clean. The relevant advisories mark glob through 14.0.1 and minimatch below 11.0.1 as affected.

Kept Capacitor on its existing major version and added a scoped npm override for the CLI's nested `rimraf` dependency: `glob@14.0.3`, resolving `minimatch@11.0.3`. After a clean `npm ci`, `npm ls` confirms the overridden versions and full `npm audit` reports 0 vulnerabilities.

Compatibility evidence: the existing Android sync command (`npm run android:sync`) and Gradle `assembleDebug` both completed; the rebuilt APK was installed and launched on Android Emulator API 36. Python/SQLite tests remain 58/58 and web tests 22/22. The web app and Android runtime payload were not changed by this development-tool dependency update; the debug APK hash remains `F7F5F42BFDD66C32D8995B8664FD55235F2022BC7E9F1E76312E384BA1615CEC`.

Artifacts: `npm-audit.json`, `dependency-tree.txt`, the exact package manifest/lockfile, and `android-emulator-v88-1080x2400.png`.

Advisories: [glob GHSA-3g3m-2fjr-6pw4](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4) and [minimatch GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
