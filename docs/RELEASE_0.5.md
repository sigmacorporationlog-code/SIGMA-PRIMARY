# SIGMA Primaire — Release 0.5 Commerciale

Cette version transforme le MVP 0.4 en base de pré-production.

## Nouveautés
- endpoint système `/api/system/status`;
- sauvegarde SQLite cohérente par API;
- archivage ZIP de la base et des médias;
- liste et téléchargement des sauvegardes;
- permissions dédiées aux sauvegardes;
- correction de l'import `FileResponse` pour les logos/timbres;
- version applicative 0.5.0.

## Politique de sauvegarde recommandée
1. Une sauvegarde automatique quotidienne sur le serveur.
2. Une copie externe hebdomadaire (clé USB/NAS/cloud).
3. Tester régulièrement la restauration sur une machine séparée.
4. Ne jamais exposer directement le port SIGMA à Internet sans VPN/proxy sécurisé.

## Compilation Windows
- `setup.bat`
- `build_exe.bat`
- puis compilation de `installer/SIGMA-Setup.iss` avec Inno Setup.
