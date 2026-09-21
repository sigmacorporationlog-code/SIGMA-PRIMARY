# SIGMA 2.18.0 — sauvegardes robustes et résilience serveur

## Objectif
Renforcer la sauvegarde locale du serveur SIGMA avant la Release Candidate commerciale.

## Nouveautés
- sauvegarde SQLite via le mécanisme natif `backup` ;
- contrôle `PRAGMA integrity_check` de la copie avant archivage ;
- manifeste JSON versionné (`format=2`) ;
- SHA-256 et taille de chaque fichier sauvegardé ;
- validation complète de l'archive ZIP avant publication ;
- écriture atomique : archive temporaire puis `os.replace` ;
- détection des archives corrompues ou altérées dans la liste des sauvegardes ;
- version de l'application portée à `2.18.0-primary-commercial`.

## Limitation volontaire
La restauration automatique n'est pas exposée comme opération distante. Une restauration devra être traitée comme une opération administrative contrôlée, avec vérification de l'archive avant remplacement de la base active.
