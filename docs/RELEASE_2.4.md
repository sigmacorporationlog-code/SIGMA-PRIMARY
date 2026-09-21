# SIGMA 2.4.0 — Synchronisation contrôlée des états des notes

Cette version durcit la synchronisation académique autour du cycle :

`draft → submitted → checked → validated → locked → published`

## Garanties
- les transitions synchronisées utilisent l'opération `transition` ;
- une transition doit être exactement l'étape suivante ;
- les transitions sont historisées dans `grade_state_history` ;
- les permissions sont distinguées entre saisie, modification, validation, verrouillage et publication ;
- les notes d'une période clôturée/publiée ne peuvent plus être modifiées ou faire l'objet d'une transition via la synchronisation ;
- une note créée offline ne peut être créée qu'en `draft` ou `submitted` ;
- les modifications de notes verrouillées/publiées restent interdites ;
- l'idempotence du journal de synchronisation est conservée.

## Vérification
La suite de tests doit couvrir les transitions valides/invalides, la clôture de période, l'audit et l'idempotence avant livraison de l'archive.
