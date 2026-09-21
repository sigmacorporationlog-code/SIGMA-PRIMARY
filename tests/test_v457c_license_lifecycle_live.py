"""Test vivant (base SQLite réelle, pas seulement statique) du cycle complet
émission -> activation d'une licence, tel qu'exercé par les nouvelles pages
static/licenses.html (superadmin) et static/administration.html (établissement).

Isolé dans un sous-processus avec sa propre DATABASE_URL : le module
app.core.database crée son moteur SQLAlchemy à l'import, donc partager le
processus pytest avec d'autres tests risquerait de figer une DB déjà
importée ailleurs dans la session.

Ce test aurait détecté le bug réel trouvé pendant le développement :
`control_plane_overview` utilisait `School` sans l'importer dans
app/services/cloud.py, ce qui faisait planter (NameError, HTTP 500) le
tableau de bord des licences dès qu'un superadmin l'ouvrait — un bug que
les tests statiques existants (assertions sur le texte source) ne peuvent
pas voir puisqu'ils ne exécutent jamais le code.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = """
import os, sys
os.environ["DATABASE_URL"] = {db_url!r}
sys.path.insert(0, {root!r})

from alembic.config import Config
from alembic import command

cfg = Config(str({root!r} + "/alembic.ini"))
cfg.set_main_option("script_location", str({root!r} + "/alembic"))
command.upgrade(cfg, "head")

from app.core.database import SessionLocal
from app.models.organization import School, Organization
from app.services.cloud import (
    issue_license_key, activate_license, subscription_state,
    control_plane_overview, ensure_default_plans,
)

db = SessionLocal()
org = Organization(name="Groupe Test")
db.add(org); db.flush()
school = School(name="Etablissement Test", organization_id=org.id, currency="XAF", language="fr")
db.add(school); db.commit(); db.refresh(school)
ensure_default_plans(db)

issued = issue_license_key(db, school.id, "standard", 365)
assert issued["license_key"].startswith("SIGMA-STANDARD-")

activated = activate_license(db, school.id, issued["license_key"])
assert activated["status"] == "active"
assert activated["active"] is True
assert activated["days_remaining"] == 365

try:
    activate_license(db, school.id, "SIGMA-CLE-INVALIDE-000000000000")
    raise SystemExit("Une cle de licence invalide a ete acceptee")
except ValueError:
    pass

overview = control_plane_overview(db)
assert overview["counts"]["total"] == 1
assert overview["counts"]["active"] == 1
assert overview["schools"][0]["school"]["name"] == "Etablissement Test"

db.close()
print("OK")
"""


def test_license_issue_then_activate_lifecycle_on_real_sqlite_db(tmp_path):
    db_path = tmp_path / "sigma_license_lifecycle_test.db"
    # as_posix() + repr(): construire une URL SQLite lisible par SQLAlchemy
    # sur toutes les plateformes, puis l'injecter dans le script généré via
    # repr() pour que Python échappe correctement les antislashs Windows
    # (ex: C:\\Users\\...) plutôt que de les laisser interprétés comme des
    # séquences d'échappement (\\U... provoquait un SyntaxError/
    # UnicodeError lors du build Windows du 19/09/2026).
    db_url = f"sqlite:///{db_path.as_posix()}"
    script = SCRIPT.format(db_url=db_url, root=str(ROOT))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "OK" in result.stdout
