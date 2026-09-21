# QUALIFICATION ENVIRONMENT FINAL

Date : 2026-09-20
Baseline : `SIGMA PRIMARY V4.46.0 — WORKSPACE P2/P3 HARDENED`
Baseline SHA-256 : `dbc9777a6b0a699fd2d59476468002236ade486780ae31045a7e47db077bbaca`

## Verdict de l'environnement

| Composant | Version / état | Statut |
|---|---|---|
| OS | Debian GNU/Linux 13 (trixie), x86_64 | AVAILABLE |
| CPU | 3 vCPU | AVAILABLE |
| Python | 3.13.5 | AVAILABLE |
| pip | 25.1.1 | AVAILABLE |
| Node | 22.16.0 | AVAILABLE |
| npm | 10.9.2 | AVAILABLE |
| Chromium | 144.0.7559.96 | AVAILABLE |
| Java | OpenJDK 21.0.11 | AVAILABLE |
| PostgreSQL server/client | absents ; `pg_config` uniquement | BLOCKED |
| Redis server/client | absents | BLOCKED |
| Docker | absent | BLOCKED |
| Android SDK / adb | absents | BLOCKED |
| Gradle standalone | absent | BLOCKED |
| Gradle wrapper | déclaré 8.9 | BLOCKED — distribution non disponible hors réseau |
| pytest | 9.0.2 | WRONG_VERSION — projet demande `<9` |

## Dépendances projet

Les paquets `bcrypt 4.2.0`, `redis 6.1.0` et `cryptography 43.0.0` sont disponibles au niveau système ; dans le venv projet, `bcrypt`/`redis` ne sont pas installés en metadata pip et sont exposés via un workspace de qualification isolé. `email-validator 2.3.0` est installé dans l'environnement Python principal.

Les dépendances qui bloquent encore l'import applicatif complet sont :

- `python-jose` — MISSING
- `psycopg` — MISSING
- `pywebpush` — MISSING

Aucune version arbitraire n'a été injectée pour contourner ces absences.
