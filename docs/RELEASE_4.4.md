# SIGMA V4.4 — Operations

## Objectif

V4.4 renforce l'exploitation commerciale et locale de SIGMA sans modifier le modèle métier : supervision, sauvegardes, maintenance et préparation des mises à jour.

## Nouveautés

- Vue d'exploitation `/api/system/operations`.
- Rotation contrôlée des sauvegardes avec conservation configurable (`MAX_BACKUPS_TO_KEEP`).
- Une sauvegarde valide récente n'est jamais supprimée par la rotation automatique.
- Les archives invalides sont conservées pour diagnostic et ne sont pas supprimées automatiquement.
- Validation hors exécution des packages SIGMA ZIP via `/api/system/release/validate`.
- Empreinte SHA-256 du package validé.
- Manifeste `release.json` embarqué dans la distribution.
- Permissions dédiées `administration.operations.view` et `administration.operations.execute`.

## Sécurité opérationnelle

La validation d'un package ne l'exécute pas et ne remplace pas une signature de code ou une chaîne de confiance de distribution. Avant un déploiement Cloud ou Windows, le package doit être distribué via un canal maîtrisé et, idéalement, accompagné d'une signature cryptographique vérifiable.

## Vérification

- `python -m compileall -q app seed.py` : OK
- `PYTHONPATH=. pytest -q` : **152 passed**
- Migration : aucune nouvelle migration nécessaire dans V4.4 (aucun nouveau modèle persistant).
