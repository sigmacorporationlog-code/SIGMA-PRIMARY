# UPDATED_ANOMALY_REGISTER — AFTER P1 REMEDIATION

| ID | Status after P1 | Evidence / decision |
|---|---|---|
| P1-001 | **PARTIALLY VERIFIED** | 4/4 static tests + 1/1 runtime Node payload test + 20/20 JS syntax; browser Chromium blocked; CSP `unsafe-inline` remains documented residual risk. |
| P1-002 | **OPEN / BLOCKED** | Fresh venv created; dependency installation blocked by DNS/network; full suite cannot execute. |
| P1-003 | **OPEN / BLOCKED** | PostgreSQL, Redis, Android SDK and Gradle distribution unavailable in qualification environment. |
| P2-001 | OPEN | Deferred by scope gate. |
| P2-002 | OPEN | CSP portion addressed as P1 defense-in-depth; broader CSP elimination of `unsafe-inline` deferred. |
| P2-003 | OPEN | Deferred. |
| P2-004 | OPEN | Deferred. |
| P2-005 | OPEN | Deferred. |
| P2-006 | OPEN | Deferred. |
| P2-007 | OPEN | Deferred. |
| P2-008 | OPEN | Deferred. |
| P2-009 | OPEN | Deferred. |
| P2-010 | OPEN | Deferred. |
| P2-011 | OPEN | Full test-suite qualification still blocked. |
| P3-001 | OPEN | Deferred. |
| P3-002 | OPEN | Deferred. |
| P3-003 | OPEN | Deferred. |
| P4-001 | OPEN | Deferred. |
