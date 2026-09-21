"""Lightweight source/release gate for SIGMA commercial builds."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
version = str(release.get("release", "")).strip()
if not version:
    raise SystemExit("release.json: release version missing")
required = [
    "run_server.py", "sigma.spec", "requirements.txt", "requirements-build.txt",
    "installer/SIGMA-Setup.iss", "installer/version.iss.inc",
    "static", "alembic", "app",
]
missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit("Missing required release paths: " + ", ".join(missing))
installer = (ROOT / "installer/SIGMA-Setup.iss").read_text(encoding="utf-8")
spec = (ROOT / "sigma.spec").read_text(encoding="utf-8")
inc = (ROOT / "installer/version.iss.inc").read_text(encoding="ascii").strip()
if '#include "version.iss.inc"' not in installer:
    raise SystemExit("Installer does not include generated version file")
if f'#define MyAppVersion "{version}"' != inc:
    raise SystemExit("installer/version.iss.inc does not match release.json")
if "__file__" in spec:
    raise SystemExit("sigma.spec must not depend on __file__")
if "UPX" in spec.upper() and "upx=False" not in spec:
    raise SystemExit("sigma.spec must explicitly disable UPX")
# Le mode onefile est incompatible avec le Gestionnaire de services Windows :
# le bootloader relance un processus enfant que le SCM ne surveille pas.
if "COLLECT(" not in spec:
    raise SystemExit("sigma.spec must build a onedir package (COLLECT) for the Windows service")
version_src = (ROOT / "app/core/version.py").read_text(encoding="utf-8")
config_src = (ROOT / "app/core/config.py").read_text(encoding="utf-8")

# app/core/version.py is the code-level projection of release.json and is the
# single source of truth consumed by Settings. Keep the release gate aligned
# with that architecture instead of requiring duplicated literal versions.
if "APP_VERSION = str(RELEASE[\"release\"])" not in version_src:
    raise SystemExit("app/core/version.py must derive APP_VERSION from release.json")
try:
    from app.core.version import APP_VERSION as source_app_version
except Exception as exc:
    raise SystemExit(f"impossible de charger la version applicative: {exc}") from exc
if str(source_app_version).strip() != version:
    raise SystemExit(
        f"app/core/version.py APP_VERSION ({source_app_version}) != release.json ({version})"
    )

expected_bindings = {
    "APP_VERSION": "APP_VERSION",
    "RELEASE_VERSION": "APP_VERSION",
}
for field, binding in expected_bindings.items():
    if f"{field}: str = {binding}" not in config_src:
        raise SystemExit(
            f"app/core/config.py: {field} must derive from app.core.version.APP_VERSION"
        )

if f'#define MyAppVersion "{version}"' not in installer:
    raise SystemExit("installer/SIGMA-Setup.iss fallback version does not match release.json")
print(f"SIGMA release gate OK: {version}")
