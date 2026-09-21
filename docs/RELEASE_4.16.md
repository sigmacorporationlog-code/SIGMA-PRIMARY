# SIGMA V4.16 — Enterprise RBAC

## Objectif
Industrialiser les habilitations sans retirer aux établissements la possibilité de personnaliser leurs postes.

## Nouveautés
- catalogue de profils RBAC : Direction, Administration scolaire, Enseignant, Comptabilité, Vie scolaire, Lecture seule ;
- création idempotente des postes et permissions d'un profil ;
- attribution d'un profil à un utilisateur avec contrôle d'établissement ;
- audit des attributions de profils ;
- une délégation ne peut plus être émise au nom d'un autre utilisateur, sauf superadmin ;
- validation des périodes de délégation.

## Sécurité
Les profils sont des modèles : aucune permission n'est attribuée automatiquement à un utilisateur. L'attribution passe par un poste (`Post`) et respecte `school_id`.

## Migration
Aucune migration SQL requise.
