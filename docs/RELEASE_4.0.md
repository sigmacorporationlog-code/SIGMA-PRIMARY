# SIGMA V4.0 — Cloud Control Plane

## Objectif
Première couche de contrôle central pour exploiter SIGMA comme produit multi-écoles commercial.

## Fonctionnalités
- catalogue d'offres Starter / Standard / Premium;
- tarification mensuelle et annuelle en XAF;
- limites utilisateurs et élèves par offre;
- fonctionnalités activables par plan;
- console de contrôle central `/api/cloud/control-plane`;
- émission de licences à durée déterminée par superadministrateur;
- activation/validation de licence côté établissement;
- snapshots mensuels d'utilisation;
- suivi du stockage média, utilisateurs, élèves et opérations de synchronisation;
- événements Cloud d'émission/activation/échec;
- conservation de la chaîne d'audit V3.8.

## Endpoints principaux
- `GET /api/cloud/plans`
- `GET /api/cloud/control-plane` (superadministrateur)
- `POST /api/cloud/license/issue` (superadministrateur)
- `POST /api/cloud/license/activate`
- `POST /api/cloud/usage/snapshot`

## Sécurité
La clé de licence en clair n'est jamais stockée en base : seul son SHA-256 est conservé. Une clé émise est renvoyée une seule fois dans la réponse de l'opération d'émission et doit être conservée par l'opérateur commercial.

## Limites connues
La V4.0 ne constitue pas encore un système de paiement SaaS automatique. La facturation récurrente, les webhooks Mobile Money/Stripe, la console web dédiée et les workers de facturation sont prévus pour la phase suivante.
