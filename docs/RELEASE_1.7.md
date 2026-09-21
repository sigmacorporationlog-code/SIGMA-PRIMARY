# SIGMA 1.7.0 — socle multi-utilisateurs & synchronisation

Cette version prépare l'exploitation réelle sur réseau local sans prétendre encore fournir la synchronisation offline complète de toutes les entités métier.

## Ajouts
- identification persistante des postes clients (`SyncDevice`);
- enregistrement/heartbeat d'un poste et suivi de dernière activité;
- état global de synchronisation: appareils, appareils actifs, file pending, conflits;
- journal d'opérations (`SyncOperation`) avec UUID d'opération et idempotence;
- version logique par entité (`SyncEntityVersion`) pour détecter les conflits au lieu d'écraser silencieusement;
- endpoints push/pull de la file de synchronisation;
- contrôle de périmètre par établissement via l'utilisateur authentifié.

## Limite volontaire
Le serveur n'applique pas encore automatiquement un payload arbitraire aux tables métier. Une opération dont `base_version` diffère de la version serveur est placée en `conflict`. Cette étape sécurise le protocole avant d'implémenter les adaptateurs de synchronisation entité par entité.

FastAPI documente les connexions persistantes/WebSockets pour les scénarios temps réel multi-clients; SIGMA 1.7 conserve ici un socle HTTP robuste avant d'ajouter le temps réel là où il apportera une vraie valeur. 
