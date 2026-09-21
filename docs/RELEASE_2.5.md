# SIGMA 2.5.0 — Reprise fiable de synchronisation

## Objectif

La version 2.5 renforce le protocole offline/online afin qu'un poste puisse reprendre une synchronisation interrompue sans rejouer aveuglément toute sa file.

## Nouveautés

- application en lot via `POST /api/sync/apply-batch` ;
- résultat individuel pour chaque opération du lot ;
- idempotence conservée pour les opérations déjà appliquées ;
- reprise exacte après interruption réseau ;
- diagnostic de la file par appareil via `GET /api/sync/devices/{device_id}/queue` ;
- prise en charge de la relation `student_guardian` dans les mutations offline ;
- résolution des identités client stables pour l'élève et le responsable ;
- contrôle établissement sur les deux côtés de la relation ;
- protection contre les doublons de liaison ;
- permission `students.modify` pour la synchronisation des liens élève-responsable ;
- validation explicite des types d'opération avant inscription dans le journal.

## Limite volontaire

Cette version renforce la couche de synchronisation serveur. Elle ne prétend pas encore fournir un miroir local complet de toutes les données permettant une consultation autonome du navigateur sans serveur. Cette étape nécessitera un véritable stockage local de lecture et une stratégie de cache/migration côté client.
