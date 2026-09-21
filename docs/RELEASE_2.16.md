# SIGMA 2.16.0 — convergence multi-postes et résolution des conflits

Cette version renforce la synchronisation des résultats d’évaluation entre plusieurs postes.

## Apports
- Un second poste utilisant la même `base_version` est placé explicitement en conflit après qu’une première opération a avancé la version serveur.
- `/api/sync/apply-batch` restitue désormais le statut `conflict` pour une collision HTTP 409 au lieu de la masquer comme un simple échec.
- Le client Python conserve ce conflit dans la file locale.
- Ajout de `resolve_conflict_remote()` pour demander au serveur un `discard` ou un `rebase`.
- Après `rebase`, la `base_version` locale est alignée sur la version serveur avant une nouvelle tentative.
- Le scénario de convergence `client A → version 1 → client B conflict → rebase → version 2` est couvert par test automatisé.

## Vérifications
- Tests automatisés : 85 réussis.
- Compilation Python et contrôles JavaScript : à effectuer avant archivage final.
- Aucun EXE Windows n’est déclaré dans cette release source.
