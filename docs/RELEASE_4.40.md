# SIGMA V4.40 — Tenant Operations & Fleet Management

## Objectif
Centraliser l'inventaire des installations SIGMA, leur état de santé, la dérive de version et la planification des déploiements progressifs.

## API
- `GET /api/system/fleet/overview` — superadmin, vue globale de la flotte.
- `POST /api/system/fleet/heartbeat` — heartbeat d'une installation autorisée.
- `POST /api/system/fleet/rollouts` — création d'un rollout canary/progressif.
- `POST /api/system/fleet/rollouts/{id}/evaluate` — évaluation et arrêt automatique si le seuil d'échec est dépassé.

## Sécurité
Les endpoints sont protégés par permission. Les utilisateurs non-superadmin restent limités à leur établissement pour les heartbeats. Les rollouts et la vue globale sont réservés au contrôle central SIGMA.

## Rollout
V4.40 ne prétend pas réaliser à elle seule un déploiement distant sans agent. Le modèle persiste l'intention, les seuils et l'état du rollout ; l'agent/deployeur existant applique ensuite l'artefact et remonte son heartbeat.

Le système est conçu pour privilégier l'arrêt (`paused`) plutôt qu'un déploiement aveugle lorsque le taux d'échec dépasse le seuil configuré.
