# SIGMA V4.25 — Pre-Production Security Certification

## Objectif
Fermer le cycle de durcissement avant mise en production commerciale en ajoutant la révocation serveur des sessions JWT et une validation automatisée des invariants d'authentification.

## Sécurité livrée
- `User.token_version` permet de révoquer immédiatement les access tokens et refresh tokens existants.
- Nouvel endpoint `POST /api/auth/logout`.
- Le middleware d'authentification refuse tout JWT dont `token_version` ne correspond plus à la version stockée en base.
- Le renouvellement refuse les refresh tokens révoqués et émet une nouvelle paire liée à la version courante.
- Migration Alembic `20260915_5200`.
- En-têtes HTTP de sécurité maintenus et HSTS activé en production.
- Audit statique automatisé `scripts/preprod_audit.py`.

## Validation
- Audit pré-production : **7/7 contrôles passés**.
- Suite complète : **197 passed, 1 warning**.
- Compilation Python : OK.

## Limites restantes
- La chaîne Alembic historique nécessite toujours un vrai rebasage initial pour garantir `alembic upgrade head` sur une base vierge sans bootstrap SQLAlchemy.
- Le rate limiting mémoire reste mono-instance ; en SaaS multi-instance, utiliser un reverse-proxy/API gateway ou Redis.
- Les connecteurs opérateurs de paiement MTN/Orange restent à intégrer séparément au noyau webhook générique.
