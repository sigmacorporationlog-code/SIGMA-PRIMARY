# REGRESSION_REPORT — P1

## Baseline comparison

The exact same pre-existing regression set was executed against:
1. immutable H4 baseline;
2. P1-fixed workspace.

Results:

| Workspace | Passed | Failed |
|---|---:|---:|
| H4 baseline | 425 | 7 |
| P1-fixed | 430 | 7 |

The five-test delta is exactly the two new P1 XSS test modules (4 static + 1 runtime). All five pass. The seven pre-existing failures are identical by test ID between baseline and P1-fixed.

Therefore there is **no detected regression introduced by P1 remediation** in the comparable automated set.

## Pre-existing failures deliberately not modified in P1

1. `test_sync_v215_evaluation_result...` — static assertion mismatch with current API implementation; outside P1 XSS/environment remediation.
2. `test_v429_endpoint_security...` — public document verification route is intentionally unauthenticated by its current product design but is not declared in that test's public exception list; deferred.
3. `test_v446_h2_finance_academic...` — environment/test shim issue (`jose.__spec__ is None`).
4. `test_v457d_first_run_admin_password...` — bcrypt missing in subprocess.
5. `test_v467_direction_profile_student_rights...` — bcrypt missing in subprocess.
6. `test_v468_cloud_backup_providers...` — bcrypt missing in subprocess.
7. `test_v4_25_security::test_refresh_rejects_malformed_subject` — existing JWT/PyJWT compatibility/test issue; deferred.

These items remain outside P1 scope and are not marked fixed.
