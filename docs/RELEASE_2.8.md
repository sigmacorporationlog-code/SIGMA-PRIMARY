# SIGMA 2.10.0 — Mode offline métier navigateur + synchronisation locale

## Objectif
La version 2.8 transforme le moteur offline 2.7 en boucle de synchronisation exploitable par un poste client: enregistrement du poste, push des opérations, application serveur, pull des mutations distantes, cache local et accusé de réception.

## Nouveautés
- `OfflineSyncStore` conservé comme journal durable outbox/inbox.
- `JsonHttpTransport` sans dépendance réseau tierce.
- `SyncClientEngine.sync_once()` avec séquence push → apply → pull → cache → ACK.
- cache local des élèves, responsables, liens famille, inscriptions et notes.
- reprise automatique logique: une erreur réseau laisse l'outbox intacte.
- détection locale des conflits persistants.
- mémorisation de l'identité client → serveur lors des créations offline.
- version applicative `2.10.0-primary-commercial`.
- installeur Inno Setup aligné sur `2.10.0`.

## Vérifications
- tests unitaires du client offline et du cycle complet avec transport simulé;
- compilation Python;
- suite complète de tests;
- archive ZIP contrôlée après packaging.

## Limites honnêtes
Le cache local de cette version est une base de lecture synchronisée. L'intégration de toutes les pages HTML avec une véritable base métier locale éditable offline, ainsi que la génération Windows EXE sur environnement Windows, restent des étapes de durcissement ultérieures.
