# SIGMA V4.35 — Performance, Capacity & Load Qualification

## Objectif

V4.35 transforme les métriques de V4.34 en un dispositif de qualification opérationnelle :
- visibilité de la capacité SQL et du pool de connexions ;
- seuil configurable de requête lente ;
- compression GZip des réponses suffisamment volumineuses ;
- endpoint `/api/system/capacity` protégé par permission ;
- probe de charge HTTP concurrente sans dépendance externe ;
- qualification reproductible avant déploiement.

## Nouveautés

### 1. Diagnostic capacité
`GET /api/system/capacity` expose :
- CPU logique détecté ;
- moteur de base ;
- état du pool SQL sur les moteurs externes ;
- limites configurées ;
- p50/p95/p99, 5xx et routes lentes ;
- avertissements de saturation ou de latence.

### 2. Compression
GZip est activé par défaut pour les réponses dépassant `GZIP_MINIMUM_SIZE` (1 KiB par défaut). Les réglages sont surchargeables via `.env`.

### 3. Probe de charge
Exemple :

```powershell
python scripts/load_probe.py --url http://127.0.0.1:8000/api/health/live --requests 500 --concurrency 25
```

Le rapport fournit débit, erreurs et p50/p95/p99.

## Critères de qualification recommandés

Pour une installation locale d'école :
- 0 erreur sur le probe health ;
- p95 < 500 ms sur les endpoints de lecture simples ;
- aucune saturation persistante du pool SQL ;
- aucun accroissement anormal du taux 5xx.

Pour un serveur mutualisé : établir les seuils avec une campagne représentative des parcours réels (élèves, notes, bulletins, finances, exports), et non uniquement avec `/health/live`.

## Validation réalisée dans l'environnement de développement

- compilation Python : PASS ;
- suite de tests : **238 passed** ;
- probe et diagnostics : couverts par tests unitaires ;
- PostgreSQL réel : non certifié dans cet environnement ;
- Windows/PyInstaller/Inno Setup : non exécutables dans cet environnement.

V4.35 ne prétend donc pas constituer une certification de capacité universelle. Il fournit les instruments pour la réaliser sur l'infrastructure cible.
