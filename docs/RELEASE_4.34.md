# SIGMA V4.34 — Observability, Auto-Healing & Safe Deployment

## Objectif
Renforcer l'exploitation production avec health/readiness enrichis, activation Windows protégée par health-check et rollback, ainsi qu'un auto-healer borné.

## Garanties
- aucune désactivation du health gate ;
- rollback disponible lorsqu'un ancien exécutable existe ;
- auto-healing limité par nombre de redémarrages et cooldown ;
- health probes limitées à des endpoints HTTP explicites ;
- aucune donnée métier ou token collecté par l'observabilité.

## Limite importante
Un seul exécutable Windows ne permet pas de promettre un zéro-downtime strict pendant un remplacement. SIGMA V4.34 fournit un **safe restart / rollback**. Le zéro-downtime réel nécessiterait au moins deux instances derrière un reverse proxy/load balancer.

## Exploitation
- `python scripts/health_probe.py --url http://127.0.0.1:8000`
- `python scripts/auto_heal.py --once`
- `python scripts/deploy_safe.py <artifact.exe>` sur Windows.
