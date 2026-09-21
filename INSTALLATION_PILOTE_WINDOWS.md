# Installation pilote Windows SIGMA

## Produit recommandé

Le pilote utilisateur final doit être installé avec `SIGMA-Setup.exe`. Il installe `SIGMA-Server.exe` comme service Windows `SIGMAPrimaireServer` et ouvre automatiquement le navigateur. Aucun terminal n'est nécessaire pendant l'utilisation.

## Package SOURCE

`setup.bat` est réservé au bootstrap/débogage technique. Il prépare les dépendances et la base mais n'est pas l'interface commerciale.

## Après installation

- Démarrage automatique de SIGMA avec Windows.
- Raccourci Bureau **SIGMA**.
- Sur le PC serveur lui-même : `http://127.0.0.1:8000/dashboard/`.
- Depuis les autres postes du réseau local (LAN) : `http://IP-DU-SERVEUR:8000/dashboard/`
  (trouvez l'IP du serveur avec `ipconfig` dans une invite de commandes, sous
  « Adresse IPv4 »). L'installateur ouvre automatiquement le port 8000 dans le
  pare-feu Windows (profils Privé/Domaine) pour que ça fonctionne sans
  manipulation supplémentaire — voir `docs/DEPLOIEMENT_COMMERCIAL_0.7.md`.
- Les journaux du service sont stockés dans `%PROGRAMDATA%\SIGMA\sigma-service.log`.
- Pour une maintenance technique, le service est visible dans `services.msc` sous **SIGMAPrimaireServer**.
- Les identifiants de première connexion sont dans `%PROGRAMDATA%\SIGMA\first-run-credentials.txt`. Le Bloc-notes les affiche une fois à la fin de l'installation. **Changez le mot de passe à la première connexion, puis supprimez ce fichier.**
- Les données (base, médias, configuration) sont dans `%PROGRAMDATA%\SIGMA`, protégées par ACL (SYSTEM et Administrateurs uniquement). Elles survivent aux mises à jour et aux désinstallations.

## Paquet portable (sans installateur)

Copiez le dossier `SIGMA-<version>-Windows-x64` en entier — l'exécutable seul ne suffit pas, il a besoin du dossier `_internal` à côté de lui.

- Démarrer : double-clic sur `SIGMA-Server.exe` (le navigateur s'ouvre seul).
- Arrêter : double-clic sur `ARRETER_SIGMA.vbs`.
- Journal : `sigma-console.log` dans le dossier de données.
