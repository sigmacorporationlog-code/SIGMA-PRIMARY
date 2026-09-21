# SIGMA v1.9.0 — Synchronisation métier contrôlée

v1.9 franchit une étape importante : le journal de synchronisation peut désormais appliquer des mutations métier réelles, mais uniquement sur un périmètre strictement blanc-listé.

## Entités activées

- `student` / **Student** : mise à jour et suppression logique.
- `guardian` / **Guardian** : mise à jour et suppression logique.

## Sécurité

- contrôle de l'établissement propriétaire ;
- contrôle de version optimiste ;
- idempotence par `operation_id` ;
- liste blanche de champs synchronisables ;
- refus des champs inconnus ;
- refus explicite des créations offline tant que les identifiants clients stables ne sont pas finalisés ;
- les mutations non supportées passent en `failed` au lieu d'être appliquées silencieusement.

## Limite volontaire

La création offline des élèves/responsables n'est pas encore activée. SIGMA doit d'abord disposer d'un identifiant client stable et d'une table de correspondance garantissant qu'une création faite hors ligne ne génère jamais de doublon après reconnexion.

Les inscriptions, évaluations, notes, bulletins et finances restent également hors de cette première whitelist métier.
