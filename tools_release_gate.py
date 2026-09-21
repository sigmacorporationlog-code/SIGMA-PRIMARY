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
config_src = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
for field in ("APP_VERSION", "RELEASE_VERSION"):
    if f'{field}: str = "{version}"' not in config_src:
        raise SystemExit(f"app/core/config.py: {field} does not match release.json ({version})")
if f'#define MyAppVersion "{version}"' not in installer:
    raise SystemExit("installer/SIGMA-Setup.iss fallback version does not match release.json")
print(f"SIGMA release gate OK: {version}")
