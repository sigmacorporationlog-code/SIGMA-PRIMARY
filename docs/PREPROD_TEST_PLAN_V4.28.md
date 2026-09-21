# SIGMA V4.28 — Qualification du périmètre de sécurité

## Objectif

Vérifier systématiquement que les endpoints manipulant un `school_id`, une classe, un élève, une carte ou un journal d’audit ne permettent pas d’accès inter-établissements.

## Correctifs contrôlés

- cartes: modèles, émission, liste, révocation, cycle de vie, téléchargement unitaire et par classe;
- niveaux et séries;
- responsables légaux et liens élève-responsable;
- journal d’audit;
- limite de pagination du journal;
- contrôle du tenant avant opération et non après mutation.

## Gates

1. `python -m pytest -q`
2. `python -m compileall -q app alembic run_server.py seed.py`
3. `alembic upgrade head` sur SQLite vierge
4. `alembic downgrade base`
5. `python scripts/release_gate.py` avec les dépendances runtime réelles
6. PostgreSQL réel
7. installation Windows réelle

Les gates 5–7 restent explicitement bloqués si l’environnement d’exécution ne possède pas les dépendances/outils nécessaires.
