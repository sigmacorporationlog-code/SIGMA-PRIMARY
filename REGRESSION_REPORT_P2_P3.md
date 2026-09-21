# REGRESSION REPORT — P2/P3

## Final executable regression
Command:
`pytest -q --ignore=tests/test_v446_correction_actions.py --disable-warnings`

Result:
- **466 PASS**
- **3 FAIL**
- **3 warnings**

All 3 failures are blocked directly by the missing `bcrypt` dependency during seed/import:
- first-run admin password test;
- bootstrapped director rights test;
- cloud backup provider isolation test.

The normally executed `tests/test_v446_correction_actions.py` module still cannot be collected because the environment lacks `bcrypt`.

## Targeted P2/P3 evidence
- RBAC/i18n/SMS/observability/academic/data/honor targeted group: **26/26 PASS**.
- Version/CI consistency: **2/2 PASS**.
- Qualification harness: **2/2 PASS**, qualification status `QUALIFIED`.

## Migration
Final head: `20260920_6340`.
Cycle verified:
`base -> 6340 -> 6330 -> 6340 -> base -> 6340` = PASS.

## Interpretation
Regression is **PARTIAL**, not green, because the missing runtime dependency prevents full execution.
