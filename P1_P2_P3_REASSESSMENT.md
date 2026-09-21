# P1 / P2 / P3 FINAL REASSESSMENT

## P1

| ID | Statut |
|---|---|
| P1-001 XSS | PARTIAL — preuves statiques/runtime locales PASS, validation navigateur réelle BLOCKED |
| P1-002 Environnement | BLOCKED — `python-jose` manquant malgré Python 3.13 et plusieurs dépendances disponibles |
| P1-003 Services réels | BLOCKED — PostgreSQL/Redis/Android/Windows indisponibles |

## P2/P3

| Domaine | Statut |
|---|---|
| RBAC | VERIFIED LOCALLY / intégration réelle non prouvée |
| i18n socle | VERIFIED LOCALLY / couverture des chaînes encore partielle |
| Tableau d'honneur | VERIFIED LOCALLY / navigateur non validé |
| Moteur académique Decimal/GPA | VERIFIED LOCALLY |
| SMS provider | VERIFIED LOCALLY / fournisseur réel non qualifié |
| Versionning/CI | VERIFIED LOCALLY |
| Observabilité | VERIFIED LOCALLY |
| Performance | PARTIAL — benchmark SQLite uniquement |
| Data validation | VERIFIED LOCALLY |
| Deployment hardening | BLOCKED réel |
| Backup/restore | PARTIAL — SQLite réel PASS, PostgreSQL BLOCKED |
| Offline/online | PARTIAL |
