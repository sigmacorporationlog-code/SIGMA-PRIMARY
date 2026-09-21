# SIGMA V3 — Foundation 3.0.0

## Objectif

Première étape technique de SIGMA V3 construite sur le socle SIGMA 2.26.0-primary-commercial, sans rupture avec les clients V2.

## Livré

- registre de notifications internes : `notifications` ;
- abonnements Web Push/PWA : `push_subscriptions` ;
- préférences de communication des responsables : `communication_preferences` ;
- bus d'événements métier léger (`DomainEvent`, `EventBus`) ;
- service de notifications ;
- endpoint `/api/notifications` ;
- endpoint d'abonnement Push ;
- recherche universelle `/api/search` ;
- premier dossier `Élève 360` `/api/students/{student_id}/360` ;
- contrôles supplémentaires d'isolation par établissement sur le pilotage ;
- migration Alembic `20260914_3000` ;
- tests de régression : 117 tests passent.

## Compatibilité

`APP_VERSION` reste `2.26.0-primary-commercial` pendant la phase Foundation afin de préserver les contrôles de compatibilité existants. `V3_VERSION` expose `3.0.0-v3-foundation`.

## Non encore livré

- WhatsApp Cloud API ;
- routage Push → WhatsApp → SMS ;
- vraie file de jobs distribuée ;
- PWA parent/enseignant complète ;
- designer Badge V3 ;
- Mobile Money ;
- moteur Insight ;
- multi-tenant commercial complet.
