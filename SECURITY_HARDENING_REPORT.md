# SECURITY HARDENING REPORT — P2/P3

## XSS / frontend injection
- P1 XSS remediation retained.
- Current static JS has no `javascript:` or `data:text/html` sinks.
- No `eval()`/`new Function()` execution was found in the application code; previous raw `eval` scanner hits were comments/identifiers (not execution).
- Dynamic business data in affected HTML contexts uses escaping or numeric normalization.
- Central CSP added.

## CSP / headers
Current middleware adds CSP and defensive headers. `unsafe-eval` is absent. `unsafe-inline` remains for the legacy inline frontend and is documented as residual hardening work.

## Secrets / sensitive files
No `.env`, private key, certificate, credentials or secret file was found in the application workspace scan. Test/benchmark password-like strings were reduced to neutral fixtures to avoid confusion with production secrets.

## RBAC
A central permission catalog is used by routes/role profiles, with `RBAC_MATRIX.md` generated from the current source. Sensitive backup/restore/upgrade/SMS/AI operations are permission-gated.

## Backup/update safety
Existing hardening for ZIP traversal, duplicate members, non-declared files, upload limits and safe restore targets is retained and covered by regression tests.

## Residual security risks
- `unsafe-inline` remains.
- Full authenticated integration tests are blocked by missing `bcrypt`.
- Real infrastructure hardening (PostgreSQL/Redis/reverse proxy/TLS) is not certifiable in this environment.
