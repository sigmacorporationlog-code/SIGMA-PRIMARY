# SIGMA 2.25.0 — Mise à niveau sécurisée

## Objectif
Introduire un cycle de mise à niveau contrôlé, sans modifier la base de production pendant la préparation.

## Fonctionnalités
- Détection de la révision Alembic courante et de la tête.
- Préparation d'une mise à niveau avec sauvegarde de sécurité automatique.
- Plan de mise à niveau persistant dans `upgrade_pending.json`.
- Exécution au démarrage, avant l'acceptation des requêtes.
- Adoption (`stamp head`) des installations historiques dont le schéma existait avant le versionnement Alembic.
- Exécution `upgrade head` pour les bases déjà versionnées.
- Rollback automatique depuis la sauvegarde de sécurité en cas d'échec.
- Endpoints administrateur : statut, préparation et annulation.
- Permissions dédiées `administration.upgrade.view` et `administration.upgrade.execute`.

## Limitation de validation
Le démarrage réel d'un service Windows et le build EXE Windows restent à valider sur un hôte Windows. Les tests disponibles dans l'environnement courant couvrent le code Python, les contrats d'API et les scripts JavaScript.
