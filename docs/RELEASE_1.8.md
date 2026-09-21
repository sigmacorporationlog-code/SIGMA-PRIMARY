# SIGMA 1.8.0 — Synchronisation contrôlée

## Objectif

La version 1.8 transforme le journal de synchronisation introduit en 1.7 en une file consommable et vérifiable, sans prétendre encore modifier automatiquement les données métier.

## Nouveautés

- vérification qu'un `device_id` appartient à l'établissement avant acceptation d'une opération ;
- protection contre la réutilisation d'un `operation_id` provenant d'un autre établissement ;
- application contrôlée d'une opération `pending` via `POST /api/sync/apply/{operation_id}` ;
- incrément atomique de la version logique de l'entité ;
- détection d'un conflit au moment de l'application si la version serveur a changé ;
- idempotence de l'application : une opération déjà `applied` est retournée sans nouvelle mutation ;
- règles de synchronisation isolées dans `app/services/sync.py` et testables indépendamment.

## Limite volontaire

`apply` valide et versionne l'opération mais ne modifie pas encore les tables métier. Cette séparation est volontaire : les handlers métier de synchronisation seront introduits progressivement afin d'éviter qu'un payload offline arbitraire puisse écraser des données scolaires critiques.

## Déploiement

Le serveur SIGMA reste le point central du LAN. Le mode offline complet nécessitera ensuite des handlers métier transactionnels, une file locale côté client et une stratégie explicite de résolution des conflits.
