# CHANGELOG — P2/P3 HARDENING

## 2026-09-20 — P2/P3 remediation
### Security / RBAC
- Centralized permission catalog and generated RBAC matrix.
- Hardened backup/restore/upgrade/SMS/AI sensitive routes.
- Retained P1 XSS/CSP hardening.

### Internationalization
- Expanded FR/EN catalog and fallback runtime.
- Added honor-board i18n migration.
- Generated current `I18N_INVENTORY.md`; full application migration remains partial.

### Academic
- Migrated academic numeric persistence to NUMERIC/Decimal.
- Explicit rounding policy and GPA modes.
- Qualification harness updated to serialize Decimal results.

### Honor board
- Configurable criteria, history, validation audit snapshots, CSV/PDF and UI history/validation actions.

### SMS
- Explicit fake vs real provider state.
- Fake simulation blocked in production by default.

### Performance
- Reduced N+1 patterns in grades, teacher assignments, dashboard aggregates and bulk workflows.
- Added reproducible ranking benchmark.

### Versioning / CI
- `release.json` is the release source of truth.
- Windows CI target aligned to Python 3.13.
- Android/Windows build metadata derives from release manifest.

### Qualification
- Final migration cycle PASS at `20260920_6340`.
- Executable regression: 466 PASS / 3 environment-blocked FAIL.
- Qualification harness: QUALIFIED.

## Release status
**Not a release candidate.** PostgreSQL, Redis, Android build and full dependency-qualified test execution remain externally blocked.

## Real Qualification — 2026-09-20
- Qualification dérivée de `SIGMA_PRIMARY_V4.46.0_WORKSPACE_P2_P3_HARDENED`.
- Correction de qualification : archive temporaire du backup renommée en `.tmp.zip` afin de satisfaire la validation `.zip` avant publication.
- Vérification réelle SQLite backup/restore : PASS.
- `mobile/android/gradlew` rendu exécutable dans le workspace Unix ; build Android réel toujours BLOCKED faute d'Android SDK/Gradle distribution.
- Régression finale : 468 PASS, 3 FAIL, 1 collection ERROR ; les quatre résultats non verts sont liés à l'absence de `python-jose`.
- PostgreSQL, Redis, Browser E2E, Android et Windows restent BLOCKED par l'environnement de qualification.
