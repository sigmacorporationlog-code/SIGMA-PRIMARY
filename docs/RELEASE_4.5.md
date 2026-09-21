# SIGMA V4.5 — Windows Commercial

V4.5 industrialise le déploiement Windows de SIGMA.

## Principales évolutions

- version fonctionnelle `4.5.0-windows-commercial`;
- bootstrap `SIGMA-Server.exe --setup`;
- génération locale d'une `SECRET_KEY` cryptographiquement aléatoire;
- génération cryptographiquement aléatoire d'un mot de passe administrateur initial si aucun secret n'est fourni, à changer obligatoirement à la première connexion;
- stockage des données persistantes sous `%PROGRAMDATA%\\SIGMA` en installation Windows;
- mode service Windows conservé via `SIGMAPrimaireServer`;
- script `bootstrap_windows.ps1`;
- installateur Inno Setup aligné sur la version 4.5.0;
- raccourcis ouvrant le tableau de bord local;
- suppression du mot de passe administrateur codé en dur dans `seed.py`;
- manifeste de release mis à jour.

## Première connexion

Après installation, consulter `%PROGRAMDATA%\\SIGMA\\first-run-credentials.txt`, se connecter avec `admin`, puis changer immédiatement le mot de passe et supprimer le fichier.

## Limitation de build

La compilation de l'EXE et de l'installateur Inno Setup doit être exécutée sur Windows avec PyInstaller et Inno Setup installés. Le code et les tests Python sont validés hors Windows ; l'artefact EXE n'est pas prétendu compilé ici.
