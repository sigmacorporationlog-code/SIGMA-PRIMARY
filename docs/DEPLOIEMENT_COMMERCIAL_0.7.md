# SIGMA Primaire — Déploiement commercial 0.5.0

## Architecture de livraison

- Serveur SIGMA installé sur un PC Windows de l'établissement.
- Serveur HTTP FastAPI exposé sur le LAN via `0.0.0.0:8000`.
- Postes clients : navigateur moderne, aucune installation Python.
- Données Windows : `%PROGRAMDATA%\\SIGMA` afin de rester inscriptibles même lorsque le programme est installé dans `Program Files`.
- Démarrage automatique facultatif via le dossier Startup Windows.
- Aucune fenêtre de console en mode commercial (`console=False` dans PyInstaller).
- Règle pare-feu TCP/8000 créée par l'installateur Inno Setup.

## Première installation

1. Compiler `SIGMA-Server` sur Windows avec Python 3.11–3.13.
2. Compiler `installer/SIGMA-Setup.iss` avec Inno Setup.
3. Installer sur le PC serveur.
4. Ouvrir le tableau de bord depuis le serveur : `http://127.0.0.1:8000/dashboard/`.
5. Depuis un client : `http://IP-DU-SERVEUR:8000/dashboard/`.
6. Changer immédiatement le mot de passe administrateur de démonstration avant la mise en production.

## Données et sauvegarde

La base SQLite et les médias sont stockés dans `%PROGRAMDATA%\\SIGMA`. Une sauvegarde commerciale doit copier ce dossier SIGMA lorsque le serveur est arrêté, ou utiliser une procédure de backup cohérente qui sera intégrée au module Backup/Restauration de la prochaine release.

## Vérifications avant commercialisation

- Tests fonctionnels des parcours inscription → évaluation → carnet/bulletin.
- Test multi-postes sur LAN.
- Test coupure Internet : le serveur local doit continuer à fonctionner.
- Test redémarrage Windows.
- Test restauration d'une copie de `%PROGRAMDATA%\\SIGMA`.
- Test d'impression PDF.
- Test des droits et des postes de responsabilité.
- Test import/export Excel.
- Test SMS avec boîtier réel avant activation du mode `http`.
