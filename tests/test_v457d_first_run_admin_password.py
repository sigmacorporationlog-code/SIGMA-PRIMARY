"""Test vivant du compte administrateur créé au premier démarrage.

Contexte : le 19/09/2026, un build Windows réel a révélé que
`seed.py` plantait (UnicodeEncodeError sur un caractère non-ASCII dans un
print()) avant d'afficher le mot de passe initial, et que ce mot de passe
était de toute façon un secret aléatoire caché dans un fichier — source de
confusion ("le mot de passe n'est pas généré"). Corrigé en :
  - retirant les caractères non-ASCII des print() de premier démarrage ;
  - générant un mot de passe initial cryptographiquement aléatoire de 24 caractères
    plutôt qu’un secret partagé/fixe ;
  - en s'appuyant sur le changement de mot de passe forcé déjà existant
    (must_change_password -> 403 PASSWORD_CHANGE_REQUIRED sur toute route
    protégée tant qu'il n'est pas changé, voir app/deps.py) pour que ce
    mot de passe connu ne soit jamais un risque une fois l'installation en
    service.

Ce test vérifie le cycle complet en conditions réelles (pas seulement une
lecture du code source) : seed.py ne plante pas, le mot de passe connu
fonctionne, l'accès reste bloqué tant qu'il n'est pas changé, et se
débloque une fois le changement effectué.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_first_run_admin_has_known_password_and_forced_change_blocks_access(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'sigma_first_run.db').as_posix()}"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    script = textwrap.dedent(f"""
        import os, sys
        os.environ["DATABASE_URL"] = {db_url!r}
        os.environ["SIGMA_DATA_DIR"] = {str(data_dir)!r}
        os.environ["SECRET_KEY"] = "test-secret-first-run-0123456789"
        sys.path.insert(0, {str(ROOT)!r})

        from alembic.config import Config
        from alembic import command
        cfg = Config({str(ROOT / "alembic.ini")!r})
        cfg.set_main_option("script_location", {str(ROOT / "alembic")!r})
        command.upgrade(cfg, "head")

        # seed.run() ne doit jamais lever d'exception, y compris sur une
        # console qui ne saurait pas encoder certains caracteres.
        import seed
        seed.run()

        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        credentials = data_dir / "first-run-credentials.txt"
        assert credentials.exists()
        report = credentials.read_text(encoding="utf-8")

        KNOWN_PASSWORD = next(line.split(":", 1)[1].strip() for line in report.splitlines() if line.startswith("Mot de passe :"))

        r = client.post("/api/auth/login", data={{"username": "admin", "password": KNOWN_PASSWORD}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["must_change_password"] is True
        token = body["access_token"]

        blocked = client.get("/api/schools", headers={{"Authorization": f"Bearer {{token}}"}})
        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "PASSWORD_CHANGE_REQUIRED"

        changed = client.post(
            "/api/auth/change-password",
            headers={{"Authorization": f"Bearer {{token}}"}},
            json={{"current_password": KNOWN_PASSWORD, "new_password": "UnAutreMotDePasseSolide987"}},
        )
        assert changed.status_code == 200, changed.text

        relogin = client.post("/api/auth/login", data={{"username": "admin", "password": "UnAutreMotDePasseSolide987"}})
        assert relogin.status_code == 200
        assert relogin.json()["must_change_password"] is False
        new_token = relogin.json()["access_token"]

        unblocked = client.get("/api/schools", headers={{"Authorization": f"Bearer {{new_token}}"}})
        assert unblocked.status_code == 200

        print("OK")
    """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "OK" in result.stdout
