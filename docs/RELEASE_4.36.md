# SIGMA V4.36 — Production Qualification & Benchmarking

V4.36 transforme la qualification de performance en processus reproductible.

## Ajouts

- `scripts/benchmark_suite.py` : benchmark HTTP reproductible et sans dépendance externe.
- Scénarios `/api/health/live` et `/api/health/ready`.
- Mesures p50/p95/p99, débit, erreurs et durée.
- Rapport JSON archivable pour chaque campagne.
- Release gate et manifeste portés en 4.36.0.
- Les résultats de benchmark sont des mesures d'environnement et ne constituent pas une capacité commerciale universelle.

## Exemple

```powershell
python scripts/benchmark_suite.py --base-url http://127.0.0.1:8000 --requests 1000 --concurrency 50 --output benchmark_report.json
```

## Qualification

Une qualification production complète nécessite encore un environnement disposant des dépendances runtime réelles, PostgreSQL et Windows Server lorsque ces plateformes sont ciblées. L'absence d'un de ces environnements bloque toute certification correspondante.
