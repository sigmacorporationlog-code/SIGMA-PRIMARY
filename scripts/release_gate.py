"""SIGMA V4.46 automated build and deployment release gate.

This gate is intentionally stricter than the portable unit-test suite: it must
run with the real runtime dependencies installed and exercises the migration
chain on a brand-new SQLite database.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn[standard]",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "email_validator": "email-validator",
    "jose": "python-jose",
    "bcrypt": "bcrypt",
    "reportlab": "reportlab",
    "openpyxl": "openpyxl",
    "multipart": "python-multipart",
    "alembic": "alembic",
    "cryptography": "cryptography",
    "psycopg": "psycopg[binary]",
    "redis": "redis",
    "PIL": "pillow",
    "qrcode": "qrcode",
    "pypdf": "pypdf",
    "docx": "python-docx",
    "pywebpush": "pywebpush",
    "httpx": "httpx",
}
REQUIRED_FILES = [
    "app/main.py",
    "app/core/security.py",
    "app/core/database.py",
    "alembic.ini",
    "alembic/versions/20260913_1600_initial_core.py",
    "installer/SIGMA-Setup.iss",
    "sigma.spec",
    "mobile/android/app/build.gradle",
    "mobile/android/app/src/main/AndroidManifest.xml",
    "mobile/android/app/src/main/java/com/sigma/school/MainActivity.java",
    "scripts/build_android.sh",
]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def main() -> int:
    failures = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).exists():
            failures.append(f"missing file: {path}")

    missing = [pkg for mod, pkg in REQUIRED_MODULES.items() if importlib.util.find_spec(mod) is None]
    if missing:
        failures.append("missing runtime dependencies: " + ", ".join(missing))

    if failures:
        for item in failures:
            print("FAIL:", item)
        print("Release gate blocked: install requirements.txt and rerun.")
        return 2

    manifest = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    expected = str(manifest.get("release", "")).strip()
    if not expected:
        return fail("release.json: release manquant")
    if manifest.get("ai_action_execution_default") is not False:
        return fail("AI action execution must remain disabled by default")
    try:
        from app.core.config import settings
        if settings.RELEASE_VERSION != expected:
            return fail(f"release.json ({expected}) != settings.RELEASE_VERSION ({settings.RELEASE_VERSION})")
    except Exception as exc:
        return fail(f"impossible de vérifier la version applicative: {exc}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    # Base dédiée à CE run, recréée à chaque fois : un fichier fixe réutilisé
    # d'un run à l'autre accumule un schéma obsolète (Base.metadata.create_all
    # ne modifie jamais une table déjà existante), et tout nouveau champ de
    # modèle ajouté depuis la dernière exécution du gate fait alors planter
    # les tests avec une erreur "no such column" sans rapport avec le vrai
    # code testé. Voir aussi la même logique déjà appliquée plus bas pour le
    # test de migration Alembic, qui utilise un TemporaryDirectory pour la
    # même raison.
    gate_db = ROOT / "unused-release-gate.db"
    if gate_db.exists():
        gate_db.unlink()
    env["DATABASE_URL"] = f"sqlite:///{gate_db.as_posix()}"

    print("== SIGMA V4.46.0 H4 RELEASE GATE ==")
    commands = [
        [sys.executable, "-m", "compileall", "-q", "app", "alembic", "run_server.py", "seed.py"],
        [sys.executable, "-m", "pytest", "-q", "tests/test_h4_security_reliability.py"],
        [sys.executable, "scripts/qualification_suite.py", "--output", str(ROOT / "qualification_report_h4.json"), "--html-output", str(ROOT / "qualification_report_h4.html")],
    ]
    for cmd in commands:
        print("RUN:", " ".join(cmd))
        if subprocess.run(cmd, cwd=ROOT, env=env).returncode != 0:
            return fail("command failed")

    with tempfile.TemporaryDirectory(prefix="sigma_gate_") as tmp:
        db = Path(tmp) / "fresh.db"
        env["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
        for cmd in ([sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "alembic", "downgrade", "20260919_5900"], [sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "alembic", "downgrade", "20260920_6100"], [sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "alembic", "downgrade", "base"]):
            print("RUN:", " ".join(cmd))
            if subprocess.run(cmd, cwd=ROOT, env=env).returncode != 0:
                return fail("Alembic migration command failed")
        if db.exists():
            print("PASS: fresh database migration lifecycle")

    if gate_db.exists():
        gate_db.unlink()

    print("PASS: V4.46 H4 release gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
