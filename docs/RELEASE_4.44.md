# SIGMA V4.44 — Mobile Offline, Secure Local Queue & Notifications

## Highlights

- Android version 4.44.0 / versionCode 44400.
- Encrypted-at-rest mobile sync queue using Android Keystore + AES-GCM.
- Trusted `SigmaMobile` JavaScript bridge, installed only inside SIGMA-origin WebView pages.
- Offline awareness and native Android notification channel.
- Foreground notification polling through the authenticated SIGMA WebView session.
- Controlled native deep links and secure download policy retained from V4.43.
- AndroidX Core dependency for notification compatibility.
- CI builds debug APK and release AAB automatically.
- Fixed GitHub Release artifact hand-off to use `sigma-android-artifacts`.

## Offline contract

The native queue stores sync intents encrypted with an Android Keystore AES key. The queue is deliberately a storage primitive: application pages decide when and how a queued operation is submitted to `/api/sync`. Invalid JSON operations are rejected before persistence.

The current release provides **offline-aware storage and notification support**, not a claim of full background offline synchronization for every screen. Background sync remains subject to Android lifecycle/network policy and should be implemented with a platform scheduler when the production sync contract is finalized.

## Notifications

SIGMA notifications are read from `/api/notifications` while the authenticated WebView is active. New notifications are surfaced through Android's native notification channel. This is a foreground notification bridge; it is not a Firebase/FCM push claim.

## Build

```bash
export SIGMA_ANDROID_BASE_URL=https://sigma.example.com/
./scripts/build_android.sh debug
./scripts/build_android.sh release
./scripts/build_android.sh bundle
```

CI installs Android SDK 35, Build Tools 35.0.0, Java 17 and Gradle 8.9.

## Certification note

Local CI/static qualification does not constitute Windows, PostgreSQL, Play Store or device certification. The current development environment does not contain the Android SDK/Gradle toolchain or the missing server runtime dependencies required by the strict release gate.
