# SIGMA Primaire — Release 1.3.0

## Objectif
Renforcer le moteur pédagogique avant la génération finale des bulletins/carnets : calculs par période, matière et compétence, appréciations configurables et circuit de validation.

## Nouveautés
- Calcul consolidé d'une période pour un élève : moyenne /20, pourcentage, matières, compétences.
- Appréciations automatiques configurables par référentiel, avec textes français et anglais.
- Circuit des résultats : `draft → submitted → checked → validated → locked → published`.
- Permissions dédiées : consultation, saisie, validation, verrouillage des résultats et configuration des appréciations.
- Traçabilité des transitions dans le journal d'audit.
- Préservation de la distinction maternelle/primaire : les cadres restent configurables et le moteur n'impose pas de notation numérique aux référentiels maternels.
- Le classement de synthèse de période ignore désormais les résultats encore en `draft`.
- Préparation renforcée du futur moteur de bulletin/carnet.

## Vérification
- `python -m compileall -q app seed.py run_server.py` : OK
- `pytest -q` : **20 tests réussis**
- `unzip -t` sur l'archive commerciale : OK
- Aucun EXE Windows n'est déclaré dans cette release.

## Réserve réglementaire
Les référentiels et appréciations de départ restent des configurations de démarrage éditables. Ils ne doivent pas être présentés comme une reproduction exacte d'un carnet MINEDUB tant que le modèle officiel correspondant n'a pas été retrouvé et vérifié dans une source primaire.
