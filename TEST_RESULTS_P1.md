# TEST_RESULTS_P1 — SIGMA PRIMARY

## P1-001 targeted evidence

| Test | Result | Evidence |
|---|---:|---|
| Static XSS security tests | **4/4 PASS** | `tests/test_p1_xss_static.py` |
| Runtime Node XSS payload test | **1/1 PASS** | `tests/test_p1_xss_runtime.py`; 7 payload classes + CSS guard |
| Inline JS syntax checks | **20/20 PASS** | every HTML page with embedded JS passed `node --check` |
| `javascript:` URL scan | **0** | full `static/` scan |
| `data:text/html` scan | **0** | full `static/` scan |
| JSON object embedded in dynamic HTML `onclick` | **0** | full `static/` scan |
| Chromium browser execution | **BLOCKED** | headless Chromium failed to terminate in container |

## P1-002 full-suite evidence

The full application suite is **not PASS**.

Comparable regression set from the application root, excluding the four-test module `test_v446_correction_actions.py` which cannot be imported without bcrypt:

- Baseline H4: **425 passed / 7 failed**.
- P1-fixed: **430 passed / 7 failed**.
- P1 adds **5 new XSS tests**, all passing.
- The seven pre-existing failures are unchanged.

Unqualified full-suite blockers:
- `bcrypt` absent.
- `python-jose` absent.
- `psycopg[binary]` absent.
- `redis` absent.
- `pywebpush` absent.
- Network/DNS unavailable for dependency installation.

## P1-003 service evidence

| Service | Result |
|---|---|
| PostgreSQL real instance | **BLOCKED** | binary unavailable, port 5432 closed |
| Redis real instance | **BLOCKED** | binary unavailable, port 6379 closed |
| Android build | **BLOCKED** | SDK unavailable; Gradle 8.9 download blocked |
