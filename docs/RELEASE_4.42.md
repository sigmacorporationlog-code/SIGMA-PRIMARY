# SIGMA V4.42 — Signed Releases & Android APK Pipeline

## Objectif

V4.42 durcit la chaîne de mise à jour automatique et prépare une compilation Android reproductible. Deux risques sont traités séparément : l'authenticité du manifeste de mise à jour et la distribution d'un client Android installable.

## Chaîne de confiance des mises à jour

Le manifeste V2 peut être signé avec **Ed25519**. L'agent de production exige une clé publique de confiance et refuse un manifeste non signé, altéré ou signé par une clé inattendue. La vérification SHA-256 de l'artefact reste obligatoire après la vérification de signature.

Flux : `manifest → signature Ed25519 → key_id → téléchargement → taille exacte → SHA-256 → activation gardée → health-check/rollback`.

La clé privée n'est jamais intégrée à SIGMA. Elle doit rester dans un coffre de secrets ou un poste de signature hors ligne.

Exemple de génération de clés :

```bash
python scripts/generate_update_keypair.py --private-out /secure/sigma-update-private.pem --public-out sigma-update-public.pem
```

Exemple de manifeste signé :

```bash
python scripts/generate_update_manifest.py SIGMA-Server.exe \
  --version 4.42.0 \
  --url https://updates.example/SIGMA-Server.exe \
  --private-key /secure/sigma-update-private.pem \
  --key-id sigma-prod-2026-01 \
  --require-signature \
  --output update-manifest.json
```

## Android APK

Un projet Android natif minimal est disponible sous `mobile/android`. Il encapsule l'interface web SIGMA dans un WebView durci : HTTPS obligatoire, navigation limitée au serveur SIGMA configuré, contenu mixte bloqué, accès `file://`/`content://` désactivé et cookies tiers désactivés.

Build local :

```bash
export ANDROID_HOME=/opt/android-sdk
export SIGMA_ANDROID_BASE_URL=https://sigma.example.com/
./scripts/build_android.sh debug
```

La CI GitHub compile automatiquement `SIGMA-Android-debug.apk`. Pour une APK commerciale signée, activer `SIGMA_ANDROID_SIGNING_ENABLED=true` et fournir les secrets de keystore documentés dans `mobile/android/README.md`.

## Limite de qualification actuelle

L'environnement de construction local de cette session ne contient pas le SDK Android ni Gradle. Le projet Android est donc vérifié statiquement et intégré à la CI, mais l'APK ne peut pas être compilée localement ici. La compilation réelle est déléguée au runner Android de GitHub Actions ou à un poste équipé du SDK Android 35.
