# SIGMA Android — V4.43

Application Android officielle SIGMA. Le client ne contient aucune donnée scolaire ni secret serveur : l'URL HTTPS est injectée au build.

## Artefacts

- Debug APK : `./scripts/build_android.sh debug`
- Release APK : `./scripts/build_android.sh release`
- Google Play App Bundle : `./scripts/build_android.sh bundle`

## Prérequis

- JDK 17+
- Android SDK 35
- Gradle 8.9
- Android Gradle Plugin 8.7.3

## Fonctions V4.43

- WebView SIGMA sécurisé HTTPS-only.
- Détection réseau et bandeau hors connexion.
- Téléchargement des bulletins/PDF via DownloadManager.
- Liens externes sortis du contexte SIGMA.
- Deep link contrôlé `sigma://open?url=...`, uniquement vers l'hôte SIGMA configuré.
- Permission notifications Android 13+ préparée pour les notifications push futures.
- APK debug, APK release et AAB release.

La signature commerciale utilise le keystore CI et ne doit jamais être committée.

## V4.44 mobile offline and notifications

The Android client now includes an encrypted local sync-intent queue backed by Android Keystore/AES-GCM, a trusted `SigmaMobile` JavaScript bridge, network/offline awareness, and native notification rendering from the authenticated SIGMA notification endpoint. This is foreground notification polling, not an FCM push guarantee.
