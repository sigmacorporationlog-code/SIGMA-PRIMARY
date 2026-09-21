# UPDATED ANOMALY REGISTER — P2/P3

| ID | Severity | Status | Evidence / note |
|---|---|---|---|
| P1-001 | P1 | PARTIALLY VERIFIED | XSS static/runtime tests pass; real Chromium proof remains blocked. |
| P1-002 | P1 | BLOCKED | Network/DNS prevents dependency installation; full qualification environment unavailable. |
| P1-003 | P1 | BLOCKED | PostgreSQL, Redis, Android SDK/Gradle real qualification unavailable. |
| P2-001 | P2 | FIXED / VERIFIED LOCALLY | Central RBAC catalog + matrix + targeted tests. |
| P2-002 | P2 | IN_PROGRESS | FR/EN runtime/fallback and 75/75 key parity; full historical literal migration remains open. |
| P2-003 | P2 | FIXED / VERIFIED LOCALLY | Configurable engine, history, validation, CSV/PDF/UI. |
| P2-004 | P2 | FIXED / VERIFIED LOCALLY | Decimal/NUMERIC migration and rounding policy. |
| P2-005 | P2 | FIXED / VERIFIED LOCALLY | Explicit GPA modes including historical overall-scale mode. |
| P2-006 | P2 | FIXED / VERIFIED LOCALLY | Explicit Fake/HTTP provider contract and production simulation guard. |
| P2-007 | P2 | FIXED / VERIFIED LOCALLY | release.json source-of-truth + consistency tests. |
| P2-008 | P2 | PARTIAL | CI target aligned; real Windows build not executable here. |
| P2-009 | P2 | FIXED / VERIFIED LOCALLY | request correlation + security headers + CSP. |
| P3-001 | P3 | PARTIAL | N+1 reductions and benchmark completed; no PostgreSQL load certification. |
| P3-002 | P3 | PARTIAL | Backup safety regression passes; cloud/restore integration remains environment-bound. |
| P3-003 | P3 | OPEN | Full UX audit still required. |
| P3-004 | P3 | PARTIAL | Security hardening pass completed; `unsafe-inline` remains. |
