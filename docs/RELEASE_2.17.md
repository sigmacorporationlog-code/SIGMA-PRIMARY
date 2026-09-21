# SIGMA 2.17.0 — convergence des données multi-postes

## Objectif

Renforcer la cohérence des données lorsqu'une même entité est créée ou modifiée depuis plusieurs postes offline.

## Corrections principales

- versionnement désormais rattaché à l'identifiant serveur canonique après une création offline ;
- `pull` expose `server_entity_id` pour permettre aux autres postes de converger vers la même identité ;
- résolution des références `*_entity_id` issues d'un autre poste avant livraison ;
- cache local `EvaluationResult` ajouté au modèle de lecture Python ;
- protection contre l'écrasement d'une donnée locale par une mutation serveur plus ancienne ;
- conservation de la correspondance identifiant client ↔ identifiant serveur lors du pull ;
- tests dédiés à la convergence inter-postes.

## Vérifications

- 89 tests automatisés réussis ;
- `compileall` réussi ;
- vérification syntaxique JavaScript réussie avec Node.js ;
- archive ZIP testée et validée.

La compilation EXE Windows reste à effectuer dans un environnement Windows adapté.
