# SIGMA v1.6.0 — Clôture de période et bulletins de classe

## Objectif
Industrialiser le cycle de fin de période pour SIGMA Primaire : clôture d'une classe, persistance des bulletins, classement configurable pour le primaire, publication et génération groupée des PDF.

## Nouveautés
- `EvaluationPeriodClosure` pour verrouiller une classe et une période.
- Clôture via `POST /api/evaluation/classes/{class_id}/period-finalize`.
- Publication via `POST /api/evaluation/classes/{class_id}/period-publish`.
- Persistance dans `ReportCard` de la moyenne, du rang, de l'effectif et de l'appréciation.
- Rang automatique désactivé pour la maternelle.
- Liste des bulletins persistés via `GET /api/evaluation/classes/{class_id}/period-report-cards`.
- Génération ZIP des bulletins publiés via `GET /api/evaluation/classes/{class_id}/period-bulletins.zip`.
- Une période clôturée interdit toute nouvelle saisie ou transition de résultat pour la classe concernée.
- Nouvelles permissions : `evaluation.periods.close` et `evaluation.periods.publish`.

## Vérification
- Compilation Python : OK
- Tests automatisés : 27/27 PASS
- Intégrité ZIP : vérifiée
- Aucun EXE Windows déclaré dans cette release.

## Positionnement réglementaire
Le moteur produit un bulletin SIGMA configurable. Il ne revendique pas reproduire un formulaire officiel MINEDUB tant qu'un modèle officiel primaire vérifié n'a pas été récupéré.
