# SIGMA V4.1.0 — Billing & Legal Governance

## Objectif
Renforcer la commercialisation de SIGMA avec une facturation d'abonnement de base et une gouvernance juridique versionnée.

## Fonctionnalités
- factures d'abonnement mensuelles/annuelles ;
- enregistrement des paiements et contrôle du dépassement ;
- passage automatique en `overdue` pour les factures échues ;
- catalogue juridique versionné ;
- empreinte SHA-256 des documents juridiques ;
- acceptation électronique horodatée ;
- traçabilité de l'IP et du user-agent lorsque disponibles ;
- autorisation de traitement/utilisation par établissement ;
- endpoints `/api/legal/*` ;
- endpoints `/api/cloud/billing/*`.

## Documents juridiques fournis
- `docs/legal/01_CONTRAT_LICENCE_SIGMA.md`
- `docs/legal/02_POLITIQUE_CONFIDENTIALITE_SIGMA.md`
- `docs/legal/03_AUTORISATION_TRAITEMENT_SIGMA.md`

## Important
Les modèles juridiques sont des bases opérationnelles. Ils doivent être complétés avec les informations exactes de l'éditeur, les conditions commerciales, les sous-traitants, l'hébergement, les durées de conservation et les clauses de droit applicable, puis relus par un professionnel du droit avant signature commerciale.

## Validation
- 147 tests passés
- compilation Python OK
- migration Alembic complète jusqu'à `20260914_4100` OK sur SQLite vierge
