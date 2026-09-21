# SIGMA Primaire — Release 2.22.0

## Service Windows natif

SIGMA Server peut désormais être installé comme **service Windows** sans dépendre de pywin32.

- Service : `SIGMAPrimaireServer`
- Exécutable : `SIGMA-Server.exe --service`
- Démarrage : automatique avec Windows
- Fonctionnement : arrière-plan, sans fenêtre CMD
- Arrêt : contrôlé proprement par le Gestionnaire de services Windows
- Redémarrage : trois tentatives progressives en cas de crash
- Journal service : `%ProgramData%\\SIGMA\\sigma-service.log`
- Le mode service n'ouvre jamais de navigateur.

## Installation

L'installateur Inno Setup crée le service, configure le pare-feu TCP 8000 et démarre le service.

## Limite de validation

Le code et les scripts sont validés dans l'environnement de développement. Le comportement SCM final doit être validé sur une machine Windows réelle, car l'environnement de développement courant n'exécute pas le Gestionnaire de services Windows.
