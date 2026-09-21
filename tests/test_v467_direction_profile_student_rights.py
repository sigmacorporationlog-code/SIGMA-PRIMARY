"""Regression : le profil "Direction" (attribue au tout premier compte de
chaque etablissement, cense avoir autorite sur l'ensemble de
l'etablissement) ne contenait que students.view -- il manquait
students.create, students.modify, students.archive et students.transfer.

Consequence observee en usage reel : un directeur ne pouvait pas ajouter
un seul eleve, meme avec "tous les droits" apparemment accordes, car ce
droit precis n'avait jamais ete inclus dans le modele de poste "Direction"
(seul le profil separe "Administration scolaire" les contenait).
"""
from pathlib import Path

from app.services.rbac_enterprise import ROLE_PROFILES

ROOT = Path(__file__).resolve().parents[1]


def test_direction_profile_has_full_student_management_rights():
    direction_perms = set(ROLE_PROFILES["direction"]["permissions"])
    required = {
        "students.view",
        "students.create",
        "students.modify",
        "students.archive",
        "students.transfer",
    }
    missing = required - direction_perms
    assert not missing, f"Le profil Direction ne peut pas gerer les eleves, il manque: {missing}"


def test_bootstrapped_director_can_create_students(tmp_path):
    # Exécuté dans un sous-processus dédié : recharger app.models en plein
    # milieu de la suite de tests pollue le registre déclaratif partagé de
    # SQLAlchemy (deux classes User distinctes coexistent alors), ce qui
    # casse des tests plus tard dans la même suite avec une erreur de join
    # sans rapport ("Don't know how to join to..."). Un sous-processus
    # isolé évite totalement ce risque.
    import subprocess
    import sys
    import textwrap

    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENV=production\nSECRET_KEY=test-secret\n"
        "SIGMA_INITIAL_ADMIN_PASSWORD=TestPassword123456!\n",
        encoding="utf-8",
    )
    script = textwrap.dedent(
        """
        import seed
        seed.run()
        from app.core.database import SessionLocal
        from app.services.rbac_enterprise import bootstrap_first_administrator
        from app.services.authorization import user_has_permission
        from app.models.security import User

        db = SessionLocal()
        director = User(
            school_id=1, username="directeur_test", email=None,
            hashed_password="x", first_name="Jean", last_name="Directeur",
            is_superadmin=False, must_change_password=True,
        )
        db.add(director)
        db.commit()
        db.refresh(director)

        post = bootstrap_first_administrator(db, 1, director, profile_code="direction")
        assert post is not None
        for perm in ("students.create", "students.modify", "students.archive", "students.transfer"):
            assert user_has_permission(db, director, perm), perm
        print("OK")
        """
    )
    env = {**__import__("os").environ, "SIGMA_DATA_DIR": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
