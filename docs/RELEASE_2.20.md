# SIGMA 2.21.0 — restauration administrateur sécurisée

## Nouveautés

- préparation d'une restauration depuis une archive ZIP SIGMA validée ;
- création automatique d'une sauvegarde de sécurité avant toute préparation ;
- staging isolé de l'archive de restauration ;
- restauration appliquée au prochain démarrage du serveur, avant l'acceptation des requêtes ;
- contrôle SQLite `PRAGMA integrity_check` avant remplacement de la base ;
- remplacement contrôlé de la base et des médias avec rollback en cas d'échec ;
- état de restauration consultable et restauration en attente annulable ;
- nouvelles permissions `administration.restore.view` et `administration.restore.execute` ;
- rejet des chemins absolus et `..` dans les manifestes de sauvegarde.

## Limites volontaires

La restauration n'est pas exécutée à chaud depuis une requête HTTP. L'administrateur prépare la restauration, puis redémarre SIGMA. Cette approche évite de remplacer une base SQLite alors que des connexions applicatives sont encore actives.

## Vérifications

- 97 tests Python passés ;
- `compileall` Python passé ;
- vérification syntaxique Node des scripts front passée ;
- archive ZIP de distribution testée avec `unzip -t`.
