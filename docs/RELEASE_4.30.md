# SIGMA V4.30 — Data Integrity & Disaster Recovery Qualification

## Objetif

V4.30 durcit la chaîne de sauvegarde/restauration et qualifie la reprise après incident avant le Release Candidate commercial.

## Contrôles

- intégrité SQLite (`PRAGMA integrity_check`) avant qu'une archive soit considérée restaurable ;
- taille maximale de l'archive, d'un fichier et du contenu total ;
- manifeste exhaustif : aucun membre ZIP non déclaré ;
- rejet des entrées ZIP dupliquées ;
- confinement strict des chemins ;
- rejet des liens symboliques lors de l'archivage des médias ;
- restauration isolée sans écrasement d'une cible non vide ;
- limite de taille sur les uploads de restauration ;
- tests de corruption, falsification, path traversal et archive non-SQLite ;
- conservation et rotation des sauvegardes existantes.

## Résultat automatisé

- **218 tests PASS**
- compilation Python PASS
- les contrôles Alembic précédemment certifiés restent requis
- le release gate runtime reste bloqué tant que `python-jose` et `bcrypt` réels ne sont pas disponibles dans l'environnement de qualification.

## Limites de cette version

La qualification complète Windows, PostgreSQL et la restauration sur une machine physique restent des gates environnementaux. Elles ne doivent pas être déclarées PASS sur la seule base de la suite locale.
