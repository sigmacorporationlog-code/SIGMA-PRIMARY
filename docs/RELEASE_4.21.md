# SIGMA V4.21 — Performance & Observability Enterprise

## Objectif
Renforcer l'exploitation multi-utilisateur avec une collecte légère des performances HTTP et un réglage explicite du pool SQL pour PostgreSQL.

## Fonctionnalités
- métriques HTTP en mémoire avec fenêtre glissante de 2 000 requêtes ;
- p50/p95/p99/max de latence ;
- taux d'erreurs HTTP 5xx ;
- compteurs par statut et routes les plus lentes ;
- endpoint protégé `GET /api/system/performance/metrics` ;
- pool PostgreSQL configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`) ;
- aucune conservation de corps de requête, token, mot de passe ou donnée personnelle dans les métriques ;
- packaging Windows historique restauré et contrôlé par les tests de compatibilité.

## Sécurité
Les métriques sont accessibles avec `administration.operations.view`. Elles restent en mémoire et sont remises à zéro au redémarrage du processus.

## Validation
185 tests passent. Un avertissement Alembic non bloquant reste présent dans la suite historique.
