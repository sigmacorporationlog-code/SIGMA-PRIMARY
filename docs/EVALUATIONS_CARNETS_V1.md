# SIGMA — Module Évaluations & Carnets v1

## Périmètre
Édition Maternelle & Primaire, francophone et anglophone. Le module est séparé des fonctionnalités du secondaire.

## Principes
- L'évaluation est référentielle: domaine → compétence → critère → activité → résultat → bilan.
- La maternelle privilégie l'observation et les appréciations qualitatives.
- Le primaire peut associer score, cote, observation et appréciation.
- Les niveaux, compétences et critères ne sont pas codés dans l'interface: ils sont des données paramétrables.
- Le PDF est produit depuis les données du référentiel et non depuis un formulaire statique.

## API principale
- GET `/api/evaluation/frameworks?school_id=&school_year_id=`
- GET `/api/evaluation/frameworks/{framework_id}`
- POST `/api/evaluation/frameworks`
- POST `/api/evaluation/domains`
- POST `/api/evaluation/competencies`
- POST `/api/evaluation/criteria`
- POST `/api/evaluation/scales`
- POST `/api/evaluation/activities`
- GET `/api/evaluation/activities?class_id=&academic_period_id=`
- GET `/api/evaluation/activities/{activity_id}/results`
- POST `/api/evaluation/activities/{activity_id}/results`
- GET `/api/evaluation/students/{student_id}/summary?academic_period_id=`
- GET `/api/evaluation/students/{student_id}/report.pdf?academic_period_id=&framework_id=`

## Données
Tables: `evaluation_frameworks`, `evaluation_domains`, `evaluation_competencies`, `evaluation_criteria`, `rating_scales`, `evaluation_activities`, `evaluation_results`.

## PDF
Le rendu contient l'identité de l'élève, l'année/période, la légende de cotation, les évaluations groupées par domaine, les observations, les zones de bilan et les trois visas enseignant/directeur/parents.

## V2 — référentiels détaillés et export classe

- Les quatre référentiels de départ (maternelle/primary × français/anglais) disposent maintenant d'un catalogue de critères détaillés et éditables.
- Les seuils du primaire sont normalisés en pourcentages configurables : NA 0–49,99 %, ECA 50–74,99 %, A 75–89,99 %, A+ 90–100 %.
- Le module conserve une évaluation qualitative pour la maternelle : l'absence de conversion automatique en note est volontaire.
- Le backend contrôle la compatibilité établissement/année entre classe, référentiel et période.
- Un export ZIP permet de générer les carnets PDF de tous les élèves actifs/conditionnels d'une classe.
- Le modèle de données reste versionné par établissement + année scolaire + section + cycle; il pourra ensuite recevoir une déclinaison par niveau sans casser les historiques.
