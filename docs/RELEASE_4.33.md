# SIGMA V4.33 — Automated Build & Deployment

## Objectif
V4.33 transforme la chaîne de livraison SIGMA en pipeline reproductible : tests → build Windows → artefact → release GitHub → déploiement explicite.

## CI
`.github/workflows/ci.yml` :
- installe les dépendances réelles ;
- exécute le release gate ;
- construit `SIGMA-Server.exe` sur `windows-latest` ;
- publie l'exécutable comme artefact ;
- sur tag `v*`, crée une GitHub Release.

## Déploiement
`.github/workflows/deploy.yml` est déclenché manuellement et exige un environnement GitHub (`staging` ou `production`). Les secrets suivants doivent être configurés :
- `SIGMA_DEPLOY_HOST`
- `SIGMA_DEPLOY_USER`
- `SIGMA_DEPLOY_PATH`

Le déploiement SSH copie l'artefact puis vérifie son SHA-256. L'activation du service applicatif reste volontairement séparée : elle doit être adaptée au serveur cible et à sa stratégie de rollback.

## Déploiement local
`python scripts/deploy_release.py <artifact> --target local-windows` copie un artefact vers `SIGMA_INSTALL_DIR` et conserve une copie précédente.

## Principe de sécurité
Aucun secret n'est stocké dans le dépôt. Aucun déploiement production automatique n'est déclenché par un simple push. La production nécessite un environnement GitHub protégé et une action manuelle.

## Certification
La présence du pipeline ne constitue pas une certification Windows/PostgreSQL. Les gates environnementaux restent exécutés dans leurs environnements réels.
