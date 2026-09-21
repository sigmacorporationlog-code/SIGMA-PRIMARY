# SIGMA V4.11 — AI Control Center

## Objectif

V4.11 ajoute le centre de contrôle opérationnel de SIGMA Intelligence. La direction peut visualiser les propositions IA, leur état et les garde-fous d’exécution depuis une interface dédiée.

## Fonctionnalités

- `GET /api/ai/actions/control-center` : vue agrégée limitée au périmètre autorisé.
- Comptage global des propositions par statut.
- Liste des propositions récentes.
- Indication de l’état d’exécution système.
- Indication de la permission `administration.ai.execute`.
- Limite maximale de destinataires affichée.
- Approbation, refus et exécution depuis l’interface dédiée.
- Isolation par établissement conservée ; un superadministrateur peut superviser l’ensemble des établissements.
- Aucune nouvelle migration : V4.11 exploite les modèles V4.9/V4.10 existants.

## Sécurité

Le principe reste : **IA → proposition → validation humaine → exécution contrôlée → audit**.

L’exécution reste désactivée par défaut via `AI_ACTION_EXECUTION_ENABLED=false`.

## Validation

- Compilation Python : OK
- Tests : 163 passed
- Migration : aucune nouvelle migration

## Interface

Nouvelle page : `/dashboard/ai-control.html`.
