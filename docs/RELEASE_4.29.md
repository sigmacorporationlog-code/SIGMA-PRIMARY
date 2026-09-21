# SIGMA V4.29 — Exhaustive Endpoint Security

## Objectif
Durcir les surfaces HTTP après V4.28 en appliquant une matrice systématique d’authentification et de périmètre.

## Correctifs
- modèles de cartes: contrôle tenant avant modification;
- impression carte individuelle: authentification + permission + tenant;
- impression classe: authentification + classe/tenant + modèle/tenant;
- émission en lot: cohérence `class_id` et `school_id`;
- vérification badge publique: limitation par IP, longueur maximale, sortie minimisée;
- correction d’un appel interne rendu invalide par la signature rate-limitée;
- configuration `BADGE_VERIFY_RATE_LIMIT` et `BADGE_VERIFY_RATE_WINDOW_SECONDS`;
- matrice statique des routes protégées;
- release gate aligné sur V4.29.

## Tests
- `PYTHONPATH=. pytest -q` : **213 passed**;
- `python -m compileall -q app tests alembic` : PASS;
- `python scripts/release_gate.py` : **BLOCKED** dans l’environnement courant si `python-jose`/`bcrypt` manquent.

## Règle de certification
Un BLOCKED du release gate reste un blocage environnemental explicite. Il ne doit pas être converti en PASS artificiel.
