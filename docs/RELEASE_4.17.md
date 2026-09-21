# SIGMA V4.17 — Parent & Teacher Portals

## Objectif

Première couche de portails dédiés pour les deux populations les plus importantes hors administration : parents/tuteurs et enseignants.

## Portail parent

- authentification SIGMA existante ;
- compte autorisé uniquement si `Guardian.user_id` correspond au compte connecté ;
- liste des enfants explicitement liés ;
- isolation établissement + lien parent/enfant ;
- classe courante ;
- bulletins publiés ;
- dernières notes publiées ;
- synthèse présences/absences/retards ;
- situation financière de l'année scolaire courante.

Endpoints :
- `GET /api/parent/me`
- `GET /api/parent/children`
- `GET /api/parent/children/{student_id}/overview`

## Portail enseignant

- année scolaire courante ;
- classes/matières réellement affectées à l'enseignant ;
- effectifs ;
- évaluations créées par l'enseignant avec saisies restantes ;
- aucun accès transversal aux classes d'autres enseignants via cette vue.

Endpoint :
- `GET /api/teacher/overview`

## Interface

- `/dashboard/parent.html`
- `/dashboard/teacher.html`

## Sécurité

Les données parentales sont déterminées par les liens `StudentGuardian`, jamais par un `student_id` fourni seul. Une tentative d'accès à un enfant non lié renvoie `404`. Les requêtes restent limitées au `school_id` du compte.

## Tests

180 tests passent. Aucun changement de schéma n'est nécessaire.
