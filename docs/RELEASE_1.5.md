# SIGMA Primaire — Release 1.5.0

## Bulletin/Carnet opérationnel

Cette version ajoute un rendu PDF de bulletin construit à partir du moteur pédagogique SIGMA.

### Nouveautés
- endpoint `GET /api/evaluation/students/{student_id}/bulletin.pdf` ;
- synthèse générale par période ;
- moyenne /20 et pourcentage ;
- appréciation automatique configurée par référentiel ;
- synthèse par matière ;
- synthèse par compétence ;
- distinction maternelle/primaire et francophone/anglophone via le référentiel ;
- identification élève/classe/année/période ;
- emplacements de commentaires, décision et signatures ;
- les résultats non finalisés restent exclus du calcul du bulletin.

### Important
Le PDF est un modèle opérationnel SIGMA. Il ne doit pas être présenté comme une reproduction exacte d'un formulaire officiel MINEDUB tant que le formulaire source officiel correspondant n'a pas été retrouvé et vérifié.

## Vérification
- compilation Python : OK
- tests automatisés : 24/24
- intégrité ZIP : OK
- EXE Windows : non construit dans cet environnement
