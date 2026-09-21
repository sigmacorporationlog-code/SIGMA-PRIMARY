# SIGMA 2.1.0 — Inscriptions synchronisables hors ligne

SIGMA 2.1 étend le protocole offline/online aux inscriptions (`ClassMembership`).

## Garanties
- une inscription peut référencer un élève par son identifiant client ou serveur ;
- l'élève doit être connu du serveur avant l'inscription ;
- la classe et l'année scolaire sont contrôlées dans le même établissement ;
- deux inscriptions actives du même élève pour la même année sont refusées ;
- les dates sont validées et converties côté serveur ;
- les suppressions d'inscription deviennent une sortie (`left_at`) plutôt qu'une suppression physique ;
- les opérations restent soumises au versionnement et à l'idempotence du protocole 2.0.

## Limite volontaire
La création automatique d'une classe ou d'une année scolaire hors ligne n'est pas autorisée. Ces référentiels restent administrés par le serveur afin d'éviter les divergences structurelles entre postes.
