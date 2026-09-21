# SIGMA 2.14.0 — Synchronisation robuste des notes offline

Cette version renforce le mode hors ligne des évaluations et notes.

## Évolutions
- opérations de notes hors ligne converties en opérations structurées `grade` du protocole `/api/sync`;
- création et modification offline distinguées;
- `base_version` conservée par note pour la détection des conflits;
- enregistrement automatique du poste navigateur auprès du serveur de synchronisation;
- application transactionnelle via `push` puis `apply-batch`;
- conservation locale des conflits au lieu de les perdre;
- version logique des notes maintenue aussi lors des saisies et transitions normales en ligne;
- lecture des notes expose `sync_version` pour permettre une base de synchronisation exacte.

## Vérification
- après validation complète de la suite de tests;
- compilation Python réussie;
- syntaxe JavaScript vérifiée avec Node.js;
- archive ZIP vérifiée.

La compilation EXE Windows n'est pas déclarée comme effectuée dans cet environnement.
