# SIGMA V4.31 — PostgreSQL & Concurrency Qualification

## Objectif

V4.31 vérifie la portabilité du schéma SIGMA vers PostgreSQL sans prétendre
avoir exécuté un serveur PostgreSQL lorsque l'environnement de qualification
n'en fournit pas.

## Tests automatisés

- Tous les modèles SQLAlchemy enregistrés sont compilés avec le dialecte PostgreSQL.
- Les index SQLAlchemy sont compilés avec le dialecte PostgreSQL.
- Les migrations Alembic sont contrôlées pour l'absence de primitives SQLite-only.
- Le driver PostgreSQL est traité comme un gate explicite (`psycopg` ou `psycopg2`).
- La suite de régression complète reste obligatoire.

## Gate environnemental

Pour exiger la présence du driver PostgreSQL :

```text
SIGMA_REQUIRE_POSTGRES=1 pytest -q tests/test_v431_postgres_qualification.py
```

La présence d'un driver ne prouve pas l'existence d'un serveur. Une vraie
qualification PostgreSQL doit utiliser `DATABASE_URL` vers une instance dédiée
et exécuter `alembic upgrade head`, la suite complète, des transactions
concurrentes et un scénario de reprise après déconnexion.

## Statut honnête

Si aucun serveur PostgreSQL réel n'est disponible, le résultat est **NON
CERTIFIÉ** pour PostgreSQL, pas PASS. SQLite reste la cible testable dans
l'environnement portable.
