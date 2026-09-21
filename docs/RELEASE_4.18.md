# SIGMA V4.18 — Onboarding établissement

## Objectif
Réduire le temps entre la création d'un établissement et sa première utilisation opérationnelle.

## Fonctionnalités
- état persistant d'onboarding par établissement ;
- création/réutilisation de l'année scolaire courante ;
- génération contrôlée des périodes ;
- préparation des profils RBAC standardisés ;
- attribution explicite du profil Direction au compte qui lance l'initialisation ;
- initialisation de l'abonnement Cloud ;
- checklist de mise en service ;
- endpoints `GET /api/onboarding/{school_id}` et `POST /api/onboarding/{school_id}/bootstrap` ;
- isolation par établissement.

## Sécurité
L'accès est limité au superadministrateur ou à l'établissement du compte courant. Les permissions restent explicites : l'onboarding ne donne pas de privilèges implicites autres que l'attribution contrôlée du profil Direction au compte initiateur.

## Migration
`20260915_4900_onboarding.py`

## Tests
Tests ciblés V4.15–V4.18 : 10 passés.
