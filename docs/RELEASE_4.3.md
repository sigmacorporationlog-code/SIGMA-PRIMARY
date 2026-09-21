# SIGMA V4.3.0 — Gouvernance juridique & Control Plane

## Ajouts
- consultation de l'historique des acceptations juridiques par utilisateur ;
- consultation de l'autorisation de traitement de l'établissement ;
- révocation explicite de l'autorisation avec date et motif ;
- état juridique versionné : une nouvelle version d'un document crée une nouvelle acceptation requise ;
- vue centrale `/api/cloud/governance` pour les superadministrateurs : établissements, licences, utilisation et factures en retard ;
- correction de l'idempotence des paiements prestataires : `external_event_id` est désormais persisté sur le paiement ;
- version applicative `4.3.0-governance-console`.

## Endpoints principaux
- `GET /api/legal/acceptances`
- `GET /api/legal/authorization`
- `POST /api/legal/authorization/revoke`
- `GET /api/cloud/governance`
- `POST /api/cloud/billing/payments/provider`

## Validation
- 149 tests passés
- compilation Python OK
- migration Alembic complète jusqu'à `20260914_4200` OK sur SQLite vierge

## Note juridique
Les documents contractuels et de confidentialité restent des modèles opérationnels. Une revue juridique locale est nécessaire avant commercialisation définitive.
