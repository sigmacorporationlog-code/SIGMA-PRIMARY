# SIGMA 2.10.0 — Mode offline métier

## Objectif
Permettre aux écrans SIGMA de continuer à consulter les données déjà chargées et de mettre en file les mutations JSON lorsque le serveur est momentanément indisponible.

## Nouveautés
- IndexedDB navigateur pour cache et file d’opérations.
- Cache des réponses GET JSON.
- File d’attente POST/PATCH/PUT/DELETE JSON persistante.
- Rejeu automatique à la reconnexion.
- Indicateur réseau dans l’en-tête.
- Service Worker pour le shell dashboard déjà visité.
- Protection des uploads binaires: ils restent explicitement dépendants du serveur.

## Limites
Les mutations offline sont rejouées vers les endpoints métier classiques; la résolution métier fine de conflits reste assurée par le mécanisme Sync serveur et sera approfondie pour chaque domaine. Les fichiers binaires (photos/PDF) ne sont pas promis offline.

## Vérifications
- suite complète: 66 tests réussis;
- compileall: OK;
- archive ZIP: contrôlée.
