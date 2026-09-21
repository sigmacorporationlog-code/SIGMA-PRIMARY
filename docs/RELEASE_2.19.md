# SIGMA 2.19.0 — restauration contrôlée et reprise après sinistre

Cette version ajoute une primitive de restauration **isolée et contrôlée** des sauvegardes SIGMA.

## Nouveautés

- `restore_backup_to_directory()` restaure une archive validée dans un dossier isolé.
- La restauration ne modifie jamais le `DATA_DIR` courant.
- Contrôle du manifeste et des empreintes SHA-256 avant extraction.
- Protection contre les chemins ZIP dangereux (path traversal).
- Contrôle `PRAGMA integrity_check` de la base restaurée.
- Refus d'une cible non vide afin d'éviter une restauration partielle ou destructive.
- Test de reprise sur une base SQLite réellement lisible après restauration.

## Vérifications

- 93 tests automatisés réussis.
- Compilation Python réussie.
- Archive ZIP reconstruite et vérifiée.
- Aucune restauration live exposée par l'API : la primitive reste isolée jusqu'à validation d'une procédure administrateur complète.
