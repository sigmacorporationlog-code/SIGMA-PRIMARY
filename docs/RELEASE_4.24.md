# SIGMA V4.24 — Security Hardening & Pre-Production Audit

## Objectif
Renforcer les barrières de sécurité avant industrialisation commerciale : isolation multi-tenant, autorisations à périmètre, limitation de débit et protection des webhooks.

## Durcissements livrés
- Vérification du tenant sur les associations `UserPost` et les délégations avant attribution d'une permission.
- Correction d'un risque IDOR sur la résolution des incidents : l'autorisation d'accès à l'incident est vérifiée **avant toute mutation**.
- `require_permission()` peut maintenant construire un contexte à partir des paramètres de route/query et du contexte utilisateur/session.
- Limitation de débit locale sur `/api/auth/login` pour réduire le brute-force distribué par adresse source.
- Taille maximale configurable des webhooks de paiement (`256 KiB` par défaut).
- En-têtes HTTP de durcissement : `Permissions-Policy`, `Cross-Origin-Resource-Policy`, et HSTS en production.
- Tests de sécurité dédiés : isolation inter-écoles, délégations inter-tenant, mutation d'incident et rate limiting.

## Limites connues
- Le rate limiting local protège une instance unique. Pour plusieurs instances, il doit être externalisé vers un reverse-proxy/API gateway ou Redis.
- Le bootstrap de schéma au démarrage reste distinct d'un `alembic upgrade head` vierge ; la chaîne Alembic historique n'est pas encore rebasée en migration initiale unique.
- La passerelle de paiement reste un noyau webhook générique signé : aucun connecteur MTN/Orange n'est prétendu livré dans cette version.

## Validation
- Suite complète : **197 passed, 1 warning**.
- Compilation Python : OK.
