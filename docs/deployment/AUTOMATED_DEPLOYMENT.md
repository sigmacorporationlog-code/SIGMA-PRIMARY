# Déploiement automatisé SIGMA

## Flux recommandé

```text
commit
  ↓
CI Linux
  ↓
release gate
  ↓
CI Windows
  ↓
SIGMA-Server.exe
  ↓
tag v4.34.0
  ↓
GitHub Release
  ↓
Staging manuel
  ↓
Smoke test
  ↓
Production approuvée
```

## GitHub Environments
Créer `staging` et `production`. Pour `production`, activer une approbation obligatoire avant exécution du job.

## Secrets
Configurer dans chaque environnement :
`SIGMA_DEPLOY_HOST`, `SIGMA_DEPLOY_USER`, `SIGMA_DEPLOY_PATH`.
Utiliser de préférence une clé SSH dédiée au déploiement, limitée au compte et au répertoire nécessaires.

## Rollback
Conserver au minimum les deux derniers artefacts. Le déploiement ne supprime jamais l'artefact précédent. Toute activation de service doit disposer d'une commande de rollback documentée.
