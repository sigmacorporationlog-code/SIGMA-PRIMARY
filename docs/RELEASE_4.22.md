# SIGMA V4.22 — Payment Gateway Core

## Objectif

V4.22 ajoute une couche de réception de paiements externes sécurisée et idempotente, destinée à servir de socle aux intégrations Mobile Money et passerelles de paiement réelles.

## Ajouts

- webhook générique `POST /api/payments/webhooks/{provider}` ;
- signature HMAC-SHA256 via `X-Signature` ;
- secret de webhook configurable par environnement ;
- contrôle d'âge de l'événement (`PAYMENT_WEBHOOK_MAX_AGE_SECONDS`) ;
- inbox persistante `payment_gateway_events` ;
- idempotence par `(provider, external_event_id)` ;
- normalisation des statuts `paid/success/successful/completed` ;
- rapprochement avec une facture d'abonnement SIGMA ;
- réutilisation du moteur de facturation existant pour empêcher les surpaiements ;
- traçabilité des événements reçus, ignorés, traités ou échoués.

## Variables de configuration

```text
PAYMENT_WEBHOOK_SECRET=
PAYMENT_WEBHOOK_MAX_AGE_SECONDS=300
PAYMENT_WEBHOOK_PROVIDER=generic
```

Le webhook est **désactivé par défaut** tant qu'un secret n'est pas configuré.

## Exemple de signature

La signature attendue est le HMAC-SHA256 du corps HTTP brut :

```text
X-Signature: sha256=<hexadecimal>
```

## Limites volontaires

Cette version ne prétend pas intégrer directement MTN MoMo, Orange Money ou un PSP spécifique. Elle fournit le **socle sécurisé et idempotent** sur lequel les adaptateurs officiels pourront être branchés après validation des contrats API, credentials marchands et procédures de rapprochement de chaque fournisseur.

## Validation

- 190 tests passent ;
- compilation Python OK ;
- aucune nouvelle dépendance externe ;
- migration `20260915_5100_payment_gateway.py` ;
- signature HMAC et idempotence couvertes par tests.
