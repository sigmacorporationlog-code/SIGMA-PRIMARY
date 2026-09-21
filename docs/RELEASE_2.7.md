# SIGMA 2.7.0 — Moteur client offline persistant

Cette version introduit un moteur local SQLite destiné aux postes clients SIGMA.

## Garanties
- file sortante persistante (`outbox`) ;
- reprise après fermeture/crash du poste ;
- idempotence des opérations ;
- statuts pending/retry/applied/failed/conflict ;
- stockage durable des conflits ;
- résolution locale `discard` ou `retry` ;
- réception durable des mutations serveur (`inbox`) ;
- curseur de pull persistant ;
- correspondance identifiant client → serveur ;
- fonctionnement avec la seule bibliothèque standard Python/SQLite.

## Limite volontaire
Le moteur constitue la couche locale de persistance et de protocole du client. Il ne prétend pas encore fournir l'interface graphique complète du poste client ni une synchronisation HTTP automatique permanente. Ces éléments seront branchés sur ce moteur lors de l'étape d'intégration client.
