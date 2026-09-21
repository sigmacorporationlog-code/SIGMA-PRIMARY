# SIGMA 2.21.0 — administration des sauvegardes et restaurations

## Nouveautés

- interface d'administration des sauvegardes enrichie ;
- consultation de l'état d'une restauration en attente ;
- sélection et validation d'une archive ZIP depuis l'interface ;
- confirmation explicite avant préparation d'une restauration ;
- affichage de la version et de la date de préparation ;
- annulation d'une restauration en attente depuis l'interface ;
- échappement des valeurs affichées dans le tableau des sauvegardes ;
- conservation du mécanisme sécurisé de restauration au redémarrage avec sauvegarde de sécurité et rollback.

## Vérifications

- 97 tests Python passés ;
- `compileall` Python passé ;
- scripts JavaScript de `administration.html` vérifiés avec `node --check` ;
- archive ZIP de distribution vérifiée avec `unzip -t`.
