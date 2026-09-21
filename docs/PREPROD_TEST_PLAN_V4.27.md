# SIGMA V4.27 — Plan de recette pré-production

## Objectif

Vérifier SIGMA comme produit déployable, migrable et isolé multi-établissement,
et non uniquement comme suite de tests unitaires.

## Gates obligatoires

1. Dépendances runtime réelles (`bcrypt`, `python-jose`, FastAPI, SQLAlchemy, etc.).
2. Compilation complète.
3. Suite de régression complète.
4. Import de tous les modules API.
5. Base SQLite vierge: `alembic upgrade head`.
6. Retour arrière: `alembic downgrade base`.
7. Upgrade d'une base de la version précédente.
8. Deux établissements: aucun accès croisé par identifiant connu.
9. Authentification réelle: hash bcrypt, access JWT, refresh JWT, révocation.
10. Uploads: taille, extension, confinement du chemin et téléchargement autorisé.
11. Exports: élèves, bulletins, cartes, reçus et sauvegardes.
12. Paiement: signature, âge, idempotence et séparation tenant.
13. Portails parent/enseignant: liens explicites et affectations.
14. IA: données externes désactivées par défaut et actions IA désactivées par défaut.
15. Backup/restore: sauvegarde, restauration, contrôle d'intégrité.
16. Windows: installation, service, démarrage, arrêt et conservation des données.
17. PostgreSQL: démarrage et migrations sur un serveur de test.
18. Test de charge: p95/p99 et absence d'erreurs 5xx sous charge nominale.

## Règle de certification

- **PASS**: comportement vérifié avec environnement réel.
- **FAIL**: comportement incorrect ou test reproductiblement échoué.
- **BLOCKER**: fonctionnalité non vérifiable dans l'environnement disponible ou
  défaut de sécurité/intégrité.

Aucune certification commerciale finale ne doit être annoncée tant qu'un
BLOCKER n'est pas levé.
