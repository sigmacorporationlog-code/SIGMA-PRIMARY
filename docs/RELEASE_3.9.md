# SIGMA V3.9 — Production & Exploitation

## Objectif

Transformer la base V3.8 en socle exploitable en production avec des diagnostics
fiables, une meilleure observabilité et des garde-fous de sécurité.

## Livré

- `/api/health/live` : liveness sans dépendance à la base.
- `/api/health/ready` : readiness avec contrôle DB + stockage, HTTP 503 si non prêt.
- `/api/system/health` : diagnostic détaillé réservé à la permission `administration.system.view`.
- `/api/system/security-posture` : contrôles de configuration sensibles.
- Contrôle de fraîcheur des sauvegardes et validation des archives existantes.
- Middleware `X-Request-ID` pour la traçabilité des requêtes.
- En-têtes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.
- En environnement `production`, une `SECRET_KEY` absente bloque le démarrage.
- Catalogue de permissions enrichi avec `administration.system.view`.

## Validation

- `python -m compileall -q app tests seed.py` : OK
- `PYTHONPATH=. pytest -q` : **139 passed**

## Limites connues

- Le diagnostic ne remplace pas un système de monitoring externe (Prometheus/Grafana,
  Sentry ou équivalent).
- Pour un déploiement Cloud à forte volumétrie, PostgreSQL reste recommandé plutôt que SQLite.
- La planification distante des sauvegardes et la console Cloud d'administration globale
  restent des étapes ultérieures.
