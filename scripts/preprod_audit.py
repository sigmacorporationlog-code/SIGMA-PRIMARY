"""Static pre-production certification checks for SIGMA V4.25.

This audit intentionally avoids importing the application so it can run even on
an offline build machine before Python dependencies are installed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks = []

def check(name, ok):
    checks.append((name, bool(ok)))

security = (ROOT / "app/core/security.py").read_text(encoding="utf-8")
deps = (ROOT / "app/deps.py").read_text(encoding="utf-8")
auth = (ROOT / "app/api/auth.py").read_text(encoding="utf-8")
model = (ROOT / "app/models/security.py").read_text(encoding="utf-8")
migration = ROOT / "alembic/versions/20260915_5200_auth_token_version.py"

check("User.token_version", "token_version" in model)
check("Access token carries token_version", '"token_version": user.token_version' in auth)
check("Refresh token carries token_version", "token_version=user.token_version" in auth)
check("Authentication validates token version", "payload.get(\"token_version\"" in deps)
check("Logout endpoint", '@router.post("/logout")' in auth)
check("Token revocation migration", migration.exists())
check("Production HSTS", 'Strict-Transport-Security' in (ROOT / "app/main.py").read_text(encoding="utf-8"))

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"[{'OK' if ok else 'FAIL'}] {name}")
if failed:
    raise SystemExit(f"Pre-production audit failed: {', '.join(failed)}")
print(f"Pre-production audit: {len(checks)}/{len(checks)} checks passed")
