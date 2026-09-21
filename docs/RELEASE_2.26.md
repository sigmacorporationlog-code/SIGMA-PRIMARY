# SIGMA v2.26.0 — Mise à jour contrôlée des postes clients

- Manifest de version avec SHA-256 et taille attendue.
- Téléchargement limité à HTTPS ou `file://` pour les tests/réseaux locaux.
- Vérification d'intégrité avant installation.
- Refus automatique des changements de major.
- Sauvegarde de l'arbre client avant remplacement.
- Remplacement atomique et rollback en cas d'échec.
- Conservation d'une trace `update.json` dans la sauvegarde précédente.

La mise à jour n'exécute aucun binaire téléchargé pendant la phase de validation.
