#!/bin/sh
# Compile l'application Android SIGMA (wrapper WebView natif — voir
# mobile/android/README.md). Référencé par ce README depuis la V4.43 mais
# manquant de la livraison : recréé ici avec le même contrat.
#
# Usage :
#   ./scripts/build_android.sh debug              # APK de test, non signé
#   ./scripts/build_android.sh release             # APK de production
#   ./scripts/build_android.sh bundle              # .aab pour Google Play
#
# Variables d'environnement reconnues (voir android/app/build.gradle) :
#   SIGMA_BASE_URL             URL HTTPS de l'établissement/serveur SIGMA
#                               ciblé par l'application (obligatoire pour un
#                               vrai APK de production — sinon l'app pointe
#                               vers https://sigma.invalid/).
#   SIGMA_APP_CHANNEL          étiquette libre (défaut: "commercial").
#   SIGMA_ANDROID_KEYSTORE           chemin vers le keystore de signature
#                               (release/bundle uniquement — sans elle,
#                               l'APK release sort non signé).
#   SIGMA_ANDROID_KEYSTORE_PASSWORD  mot de passe du keystore.
#   SIGMA_ANDROID_KEY_ALIAS          alias de la clé dans le keystore.
#   SIGMA_ANDROID_KEY_PASSWORD       mot de passe de cette clé.
#
# Aucun secret n'est jamais lu depuis un fichier commité : uniquement depuis
# l'environnement, au moment du build.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANDROID_DIR="$SCRIPT_DIR/../android"
TARGET="${1:-debug}"

cd "$ANDROID_DIR"

PROP_ARGS=""
if [ -n "${SIGMA_BASE_URL:-}" ]; then
  PROP_ARGS="$PROP_ARGS -PSIGMA_BASE_URL=$SIGMA_BASE_URL"
fi
if [ -n "${SIGMA_APP_CHANNEL:-}" ]; then
  PROP_ARGS="$PROP_ARGS -PSIGMA_APP_CHANNEL=$SIGMA_APP_CHANNEL"
fi

case "$TARGET" in
  debug)
    echo "[SIGMA Android] Build DEBUG (non signé, pour test uniquement)"
    ./gradlew assembleDebug $PROP_ARGS
    echo "APK : app/build/outputs/apk/debug/app-debug.apk"
    ;;
  release)
    if [ -z "${SIGMA_ANDROID_KEYSTORE:-}" ]; then
      echo "[SIGMA Android] ATTENTION : SIGMA_ANDROID_KEYSTORE non défini — l'APK release sortira NON SIGNÉ."
      echo "Un APK non signé ne s'installe pas sur un téléphone en dehors du mode développeur."
    fi
    echo "[SIGMA Android] Build RELEASE"
    ./gradlew assembleRelease $PROP_ARGS
    echo "APK : app/build/outputs/apk/release/app-release.apk"
    ;;
  bundle)
    if [ -z "${SIGMA_ANDROID_KEYSTORE:-}" ]; then
      echo "[SIGMA Android] ERREUR : un .aab destiné à Google Play doit être signé."
      echo "Définissez SIGMA_ANDROID_KEYSTORE / _PASSWORD / _KEY_ALIAS / _KEY_PASSWORD avant de relancer."
      exit 1
    fi
    echo "[SIGMA Android] Build BUNDLE (.aab, Google Play)"
    ./gradlew bundleRelease $PROP_ARGS
    echo "Bundle : app/build/outputs/bundle/release/app-release.aab"
    ;;
  *)
    echo "Usage: $0 {debug|release|bundle}" >&2
    exit 1
    ;;
esac
