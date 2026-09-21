# SIGMA 2.3.0 — Synchronisation académique contrôlée

Cette release étend le protocole offline/online aux **notes (`Grade`)**. Une note peut être créée hors ligne pour une évaluation existante et un élève déjà connu du serveur ou résolu via son identité client.

## Garanties
- évaluation existante et située dans le même établissement ;
- élève existant et inscrit dans la classe de l’évaluation ;
- une seule note par élève et évaluation ;
- création limitée aux états `draft` ou `submitted` ;
- modification d’une note `locked` ou `published` refusée ;
- suppression de note interdite par synchronisation ;
- permission `academic.grades.enter` exigée pour les mutations de notes ;
- permissions `students.create` / `students.modify` conservées pour les entités élèves/inscriptions ;
- identités client stables et idempotence conservées.

La synchronisation ne modifie pas automatiquement les évaluations, matières ou classes : ces référentiels restent administrés côté serveur.
