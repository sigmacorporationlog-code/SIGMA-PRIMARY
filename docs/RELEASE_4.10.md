# SIGMA V4.10 — AI Execution Engine

## Objectif

V4.10 complète la boucle SIGMA Intelligence : une proposition IA peut être approuvée puis exécutée par un exécuteur spécialisé, avec contrôles d'autorisation, périmètre établissement, garde-fou système, idempotence et audit.

## Actions prises en charge

- `communication_draft` : envoi via le moteur SIGMA Connect après validation ;
- `finance_reminder` : relance des responsables liés aux factures sélectionnées ;
- `pedagogy_remediation` : création d'une notification de remédiation pour l'utilisateur validateur ;
- `report_generation` : génération d'un rapport PDF administratif.

## Sécurité

L'exécution est **désactivée par défaut** avec `AI_ACTION_EXECUTION_ENABLED=false`. Elle nécessite la permission `administration.ai.execute` en plus de `administration.ai.use`. Les propositions restent limitées à leur `school_id`, et les actions sont refusées si leur périmètre contient des données d'un autre établissement.

Chaque proposition possède une `execution_key` unique. Une proposition déjà exécutée est idempotente. Les exécutions sont inscrites dans le journal d'audit.

## Configuration

```env
AI_ACTION_EXECUTION_ENABLED=false
AI_ACTION_MAX_RECIPIENTS=100
```

Pour activer l'exécution, l'administrateur doit explicitement modifier la configuration puis redémarrer le serveur.

## API

`POST /api/ai/actions/proposals/{id}/execute`

Une action doit être dans l'état `approved`. Les états finaux sont `executed`, `rejected` ou `expired`.

## Validation

- compilation Python : OK
- tests : 162 passed
- migration Alembic jusqu'à `20260914_4500` : OK

Cette version ne remplace pas un audit de sécurité ou une revue juridique de production.
