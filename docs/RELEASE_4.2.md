# SIGMA V4.2 — Billing Automation & Subscription Lifecycle

## Objectif
V4.2 transforme la facturation Cloud en cycle exploitable : renouvellement idempotent, suivi des impayés, période de grâce, suspension automatique et réactivation après paiement.

## Livré
- Facture de renouvellement calculée à partir de la fin d'abonnement.
- Anti-duplication des factures par période et établissement.
- Période de grâce configurable (`grace_period_days`, 7 jours par défaut).
- Suspension automatique après expiration + fin de grâce.
- Réactivation automatique lorsqu'une facture de renouvellement est réglée.
- Paiements provenant d'un prestataire avec `external_event_id` idempotent.
- Endpoint de réconciliation du cycle d'abonnement.
- Paiement intégral : extension de l'abonnement jusqu'à la période facturée.

## API
- `POST /api/cloud/billing/renewals`
- `POST /api/cloud/billing/reconcile`
- `POST /api/cloud/billing/payments/provider`

Les opérations de contrôle central sont réservées au superadministrateur.

## Migration
`20260914_4200_billing_automation.py` ajoute les contrôles sans dépendre de la réflexion SQLite des tables cœur héritées.

## Vérification
- Compilation Python : OK
- Tests : **149 passed**
- Migration Alembic jusqu'à `20260914_4200` : OK sur SQLite de validation

## Limite volontaire
Les connecteurs directs MTN Mobile Money / Orange Money et leurs webhooks propriétaires restent séparés de ce noyau. V4.2 fournit le point d'idempotence et le traitement commun nécessaires à leur branchement sécurisé.
