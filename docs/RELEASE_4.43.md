# SIGMA V4.43 — Android Productization & Signed Update Chain

## Highlights

- Android application shell hardened for HTTPS-only SIGMA deployments.
- Offline/network awareness banner.
- Controlled `sigma://open` deep links restricted to the configured SIGMA host.
- Android notification permission prepared for Android 13+.
- PDF/download handling through Android DownloadManager with same-origin checks.
- Automated debug APK and release AAB compilation in GitHub Actions.
- Signed release APK + AAB supported through CI secrets.
- Ed25519 trusted update manifests retained from V4.42.

## Android artifacts

| Artifact | Build | Purpose |
|---|---|---|
| `SIGMA-Android-debug.apk` | `assembleDebug` | QA / device testing |
| `SIGMA-Android-release.aab` | `bundleRelease` | Google Play submission |
| `SIGMA-Android.apk` | signed `assembleRelease` | direct commercial distribution |
| `SIGMA-Android.aab` | signed `bundleRelease` | signed Play release |

The current execution environment does not contain the Android SDK/Gradle, so local APK/AAB compilation is delegated to the CI runner. This is a build-environment limitation, not a claim that the artifacts were locally compiled here.
