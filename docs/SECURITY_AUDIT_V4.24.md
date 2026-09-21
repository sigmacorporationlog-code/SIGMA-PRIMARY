# SIGMA — Audit de sécurité pré-production V4.24

Date : 2026-09-15

## Résumé
V4.24 traite plusieurs classes de défauts applicatifs fréquents avant une mise en production commerciale : IDOR, traversée de tenant par associations d'autorisation, brute-force de connexion et payloads webhook excessifs.

## Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| Isolation d'un `UserPost` appartenant à une autre école | PASS |
| Isolation d'une délégation appartenant à une autre école | PASS |
| Résolution d'un incident d'un autre tenant sans mutation préalable | PASS |
| Rate limiting local de connexion | PASS |
| Signature HMAC webhook | PASS |
| Limitation de taille webhook | PASS |
| En-têtes de sécurité HTTP | PASS |
| Régression fonctionnelle complète | PASS — 197 tests |

## Menaces couvertes

### IDOR / Broken Object Level Authorization
La résolution d'un incident vérifie désormais le tenant dans le service métier avant de modifier l'objet. Le contrôle n'est donc plus uniquement placé dans la couche HTTP.

### Cross-tenant authorization
Les postes et délégations utilisés pour calculer les permissions sont filtrés sur le `school_id` de l'utilisateur. Une relation mal configurée ne doit pas devenir un canal de traversée inter-écoles.

### Brute force
Le compte conserve son verrouillage après échecs successifs. V4.24 ajoute un garde-fou par adresse source et fenêtre temporelle.

### Webhook abuse
Les événements entrants doivent rester signés et leur taille est plafonnée avant parsing métier.

## Points restant à traiter avant une certification sécurité externe
1. Revue complète des endpoints de téléchargement/export.
2. Tests automatisés de tous les endpoints avec deux tenants réels.
3. Rotation/révocation des refresh tokens et gestion de session persistante.
4. Rate limiting distribué si SIGMA est déployé en plusieurs instances.
5. Reverse-proxy TLS avec HSTS effectif et journalisation centralisée.
6. Scan SAST/SCA et analyse des dépendances dans le pipeline CI/CD.
7. Test de restauration et reprise après sinistre sur une base de production anonymisée.
