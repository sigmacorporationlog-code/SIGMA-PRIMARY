# SIGMA 2.16.0 — Évaluations offline réellement synchronisables

Cette version corrige une distinction importante : la saisie de la page Évaluations manipule des `EvaluationResult`, et non les anciennes entités `Grade`. Le protocole offline utilise désormais `evaluation_result` avec versionnement, contrôle de classe/période, barème, verrouillage et résolution de conflits.

## Vérifications
- Tests unitaires/régression : à valider après packaging.
- Syntaxe Python et JavaScript : à valider.
- EXE Windows : non produit dans l'environnement courant.
