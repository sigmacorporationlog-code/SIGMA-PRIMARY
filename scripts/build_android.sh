#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$ROOT/mobile/android"
BASE_URL="${SIGMA_ANDROID_BASE_URL:-}"
CHANNEL="${SIGMA_ANDROID_CHANNEL:-commercial}"
BUILD_TYPE="${1:-debug}"

case "$BUILD_TYPE" in debug|release|bundle) ;; *) echo "usage: scripts/build_android.sh [debug|release|bundle]" >&2; exit 2;; esac
[[ -n "$BASE_URL" ]] || { echo "SIGMA_ANDROID_BASE_URL is required" >&2; exit 2; }
[[ "$BASE_URL" == https://* ]] || { echo "SIGMA_ANDROID_BASE_URL must use HTTPS" >&2; exit 2; }
command -v gradle >/dev/null 2>&1 || { echo "Gradle 8.9 is required. CI installs it automatically." >&2; exit 3; }
[[ -n "${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}" ]] || { echo "Android SDK is required (ANDROID_HOME or ANDROID_SDK_ROOT)." >&2; exit 3; }

case "$BUILD_TYPE" in
  debug) TASK=":app:assembleDebug";;
  release) TASK=":app:assembleRelease";;
  bundle) TASK=":app:bundleRelease";;
esac
cd "$ANDROID_DIR"
gradle --no-daemon "$TASK" -PSIGMA_BASE_URL="$BASE_URL" -PSIGMA_APP_CHANNEL="$CHANNEL"

echo "Android outputs:"
find app/build/outputs -type f \( -name '*.apk' -o -name '*.aab' \) -print
