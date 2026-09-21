# SIGMA Primaire — Release 0.9.0

## Workflow administratif du dossier élève

Cette version transforme la grille élèves en véritable point d’entrée du dossier administratif.

### Nouveautés
- Endpoint consolidé `/api/students/{student_id}/profile` : identité, inscription courante, historique des affectations et responsables.
- Vérification systématique de l’établissement pour les opérations élèves principales.
- Validation de la cohérence classe / année scolaire lors de l’inscription.
- Contrôle de capacité des classes à l’inscription et au transfert.
- Interface élèves : action **Dossier** donnant accès au profil administratif consolidé.
- Affichage des parents/tuteurs, personne principale, autorisation de retrait et historique scolaire.
- Version applicative et installeur portés à 0.9.0.
- CORS par défaut fermé et clé secrète persistante générée par l’application lorsqu’aucune clé n’est fournie.

## Intégrité
Les historiques d’affectation ne sont pas supprimés : une mutation ferme l’affectation précédente avec `left_at` et crée une nouvelle ligne.

## Vérifications
- `python -m compileall -q app seed.py run_server.py` : OK
- `pytest -q` : 11 tests passés

## Limitation
La compilation Windows `.exe` et l’installeur final doivent encore être construits sur un poste Windows équipé des dépendances de build.
