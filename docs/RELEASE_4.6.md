# SIGMA V4.6 — Security & Tenant Isolation Hardening

## Scope

V4.6 is a security-hardening release focused on multi-tenant isolation and authorization boundaries.

### Changes
- Centralized `assert_school_access()` guard for school-scoped API resources.
- Hardened user listing/detail and user-post administration against cross-school access.
- Hardened post permission administration against cross-school access.
- Hardened user-to-post assignment and delegation creation, including same-school validation.
- Hardened effectif reports with school access enforcement.
- Hardened finance fee structures and invoice creation with student/school validation.
- Hardened student payment history access.
- Hardened teacher-assignment listing by validating the academic year and class school.
- Preserved superadmin access for central administration where intended.

## Validation

- `python -m compileall -q app`: OK
- `PYTHONPATH=. pytest -q`: **152 passed**
- Existing Alembic chain remains unchanged; no schema migration required.

## Security note

The full Windows installer build must still be executed on a Windows build host with the production dependency set installed. This Linux validation covers source compilation and the automated test suite.
