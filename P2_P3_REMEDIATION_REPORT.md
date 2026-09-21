# SIGMA PRIMARY — P2/P3 REMEDIATION REPORT

## Baseline
- Baseline H4: `SIGMA_PRIMAIRE_V4.46.0_HARDENED_PRODUCTION_AUDIT_H4.zip`
- H4 SHA-256: `ef71bd7051049445307ff41676c6f0602ec2f31bb35a388a94dc8ab8ed5671ba`
- P1 workspace used as working baseline: `SIGMA_PRIMARY_4.46.0_WORKSPACE_P1_FIXED.zip`

## P1 status before this phase
- P1-001 XSS: PARTIALLY VERIFIED
- P1-002 qualification environment: BLOCKED
- P1-003 real services: BLOCKED

## P2/P3 remediation completed
### P2-001 RBAC — FIXED / VERIFIED LOCALLY
- Central permission catalog introduced and used as source of truth.
- Role profiles reconciled against the catalog.
- Sensitive read/import/export/backup/restore/upgrade/SMS/AI routes audited.
- `RBAC_MATRIX.md` generated.
- Targeted RBAC tests: PASS.
- Remaining: full production integration cannot be certified without the missing runtime dependencies/services.

### P2-002 i18n — PARTIAL
- Central FR/EN catalogs, stable keys and FR fallback are active.
- Current catalogs: 75 FR / 75 EN keys, exact key parity.
- Honor board and several shared navigation/auth surfaces migrated.
- Historical audit identified ~919 candidate literals; full application migration is intentionally NOT claimed complete.
- `I18N_INVENTORY.md` is the worklist.

### P2-003 honor board — FIXED / VERIFIED LOCALLY
- Configurable criteria engine.
- Deterministic competition ranking/ties.
- Persistent entries and audit snapshots (class, absence count, validator, validation timestamp).
- History, CSV, PDF, preview, generation and batch validation routes.
- Honor board UI now exposes history/validation and uses i18n/safe rendering.
- Migration chain through 6340 validated on SQLite.

### P2-004 academic numeric precision — FIXED / VERIFIED LOCALLY
- Academic/evaluation numeric fields migrated to NUMERIC/Decimal.
- Explicit `ROUND_HALF_UP` policy.
- Migration 6320 verified through fresh upgrade/downgrade cycles.

### P2-005 GPA — FIXED / VERIFIED LOCALLY
- Historical `overall_scale` mode retained.
- New explicit `subject_weighted` mode.
- Raw → calculation → normalization → rounding → display stages separated.
- GPA reference tests pass.

### P2-006 SMS — FIXED / VERIFIED LOCALLY
- Provider abstraction with Fake/HTTP provider distinction.
- Fake provider is not silently considered a real production send.
- Production simulation blocked by default.
- Delivery status records expose simulation state.

### P2-007 versioning — FIXED / VERIFIED LOCALLY
- `release.json` is the source of truth.
- Backend, Windows build and Android Gradle read/derive release metadata.
- Version consistency tests: 2/2 PASS.

### P2-008 Windows CI — FIXED STATICALY / BUILD BLOCKED
- CI Python target aligned to 3.13.
- Build script reads `release.json`.
- Actual Windows installer build remains unexecuted in this Linux/network-restricted environment.

### P2-009 observability — FIXED / VERIFIED LOCALLY
- Central request correlation ID.
- Secure response headers.
- Centralized CSP.
- `unsafe-eval` absent.
- `unsafe-inline` remains a documented residual constraint of the current frontend architecture.

## P3 performance/data hardening
- Grade grid writes batch student/grade/version operations.
- Teacher assignment reads batch users/subjects.
- Dashboard evolution/stats use SQL aggregation.
- Honor board ranking uses 3 SQL statements for 100–5000 students in the benchmark scenario.
- Bulk bulletin/card flows were batch-oriented in earlier hardening and retained.
- Decimal validation covers monetary/academic boundaries.
- Backup archive safety remains tested for traversal, duplicate members, invalid SQLite and non-empty restore targets.

## Material remaining work
- Full i18n migration of all identified UI literals.
- True PostgreSQL qualification.
- True Redis qualification.
- Real Android build/sign/install/runtime qualification.
- Full pytest suite including modules blocked by bcrypt.
- PostgreSQL/Redis concurrency and large-load certification.
- Full UX pass.
- Removal of `unsafe-inline` after frontend CSP migration to non-inline scripts/styles.

## Gate interpretation
P2/P3 work is **PARTIAL**, not a release candidate. The implemented fixes are materially stronger, but several gates are blocked by the qualification environment and some P2 items are intentionally only partially migrated.
