# SIGMA Primaire — Release 2.13.0

## Offline-first Évaluations & Notes

- Cache IndexedDB normalisé pour évaluations et lignes de notes.
- Hydratation locale après consultation en ligne des évaluations et notes.
- Consultation des notes depuis le cache lorsque le serveur est indisponible.
- Enregistrement local immédiat des notes hors ligne.
- Mise en file de la saisie de notes pour synchronisation à la reconnexion.
- Validation locale du barème (`0 <= note <= max_score`).
- Refus local des modifications de notes verrouillées/publiées.
- Persistance après rechargement de la page via IndexedDB.

## Limite volontaire

La synchronisation serveur des écritures de notes reste soumise aux contrôles métier et de concurrence du protocole SIGMA. Cette version améliore la continuité hors ligne du navigateur sans prétendre fournir une E2E navigateur complète tant qu'un navigateur automatisé n'est pas disponible dans l'environnement de validation.
