# SIGMA Primaire 2.25.0

## Compatibilité client/serveur
- endpoint `/api/sync/compatibility`;
- contrôle automatique avant chaque passe de synchronisation;
- clients 2.20+ du même major acceptés s'ils ne sont pas plus récents que le serveur;
- clients trop anciens, major différent ou plus récents que le serveur bloqués proprement;
- le poste reste utilisable hors ligne lorsque le serveur est incompatible.
