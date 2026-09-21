# SIGMA 4.45.1 — Pilote sans terminal & corrections réversibles

Cette version pilote ajoute un parcours Windows orienté utilisateur final et des actions de correction sécurisées.

## Corrections réversibles
- Modifier un niveau, son ordre, une série et une classe.
- Désactiver une classe/niveau/série sans effacer l'historique.
- Réactiver une ressource désactivée.
- Une classe contenant des élèves actifs ne peut pas être désactivée par erreur.
- Un niveau ou une série encore utilisé(e) par des classes actives ne peut pas être désactivé(e).
- Le changement d'année d'une classe ayant un historique d'inscriptions est bloqué pour préserver l'intégrité historique.
- Chaque correction/suppression logique est journalisée dans l'audit.

## Windows
- Le service `SIGMAPrimaireServer` démarre automatiquement.
- L'installateur ouvre automatiquement le navigateur après vérification de disponibilité.
- Le serveur est empaqueté en mode sans console (`console=False`).

## Limites de validation
La compilation réelle PyInstaller/Inno Setup doit être exécutée sur Windows avec les dépendances de production installées.

## Démarrage pilote immédiat
Si le dossier source est utilisé après `setup.bat`, double-cliquer sur `OUVRIR_SIGMA.vbs` lance le serveur avec `pythonw.exe` en arrière-plan et ouvre automatiquement le navigateur. Le terminal n'est pas nécessaire.
