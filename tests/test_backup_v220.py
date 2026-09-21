from pathlib import Path
import json
import sqlite3
import zipfile

import pytest

from app.services import backup


# Depuis le durcissement v4.30, une archive ne peut remplacer la base que si
# l'état commercial (abonnements, quotas) y est présent et de schéma identique à
# celui de la base vivante : la restauration ne doit jamais pouvoir réactiver une
# licence expirée ni relever des plafonds. Les fixtures ci-dessous fournissent
# donc le schéma minimal attendu par _preserve_and_validate_commercial_state().
_COMMERCIAL_SCHEMA = [
    "create table school_subscriptions (id integer primary key, school_id integer,"
    " plan_code text, status text, starts_on text, ends_on text,"
    " max_users integer, max_students integer)",
    "create table users (id integer primary key, school_id integer, is_active integer)",
    "create table students (id integer primary key, school_id integer, status text)",
]


def _apply_commercial_schema(con: sqlite3.Connection) -> None:
    for statement in _COMMERCIAL_SCHEMA:
        con.execute(statement)


def _make_archive(tmp_path: Path) -> Path:
    db = tmp_path / "sigma.db"
    con = sqlite3.connect(db)
    con.execute("create table t (id integer primary key, name text)")
    con.execute("insert into t(name) values ('ok')")
    _apply_commercial_schema(con)
    con.commit(); con.close()
    manifest = {"format": 2, "app_version": "2.25.0-primary-commercial", "created_at": "now", "files": [
        {"path": "sigma.db", "sha256": backup._sha256(db), "size": db.stat().st_size},
    ]}
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(db, "sigma.db")
        z.writestr("manifest.json", json.dumps(manifest))
    return archive


def test_prepare_restore_creates_safety_backup_and_pending_plan(tmp_path, monkeypatch):
    archive = _make_archive(tmp_path)
    safety = tmp_path / "safety.zip"
    monkeypatch.setattr(backup, "restore_state_path", lambda: tmp_path / "restore_pending.json")
    monkeypatch.setattr(backup, "backup_root", lambda: tmp_path / "backups")
    monkeypatch.setattr(backup, "create_backup", lambda: safety)
    safety.write_bytes(b"safety")
    plan = backup.prepare_restore(archive)
    assert plan["status"] == "pending_restart"
    assert Path(plan["archive"]).exists()
    assert Path(plan["safety_backup"]) == safety
    assert backup.get_restore_state()["token"] == plan["token"]


def test_prepare_restore_rejects_second_pending_plan(tmp_path, monkeypatch):
    archive = _make_archive(tmp_path)
    state = tmp_path / "restore_pending.json"
    state.write_text(json.dumps({"token": "existing"}), encoding="utf-8")
    monkeypatch.setattr(backup, "restore_state_path", lambda: state)
    with pytest.raises(RuntimeError, match="déjà en attente"):
        backup.prepare_restore(archive)


def test_apply_pending_restore_replaces_database_and_cleans_plan(tmp_path, monkeypatch):
    archive = _make_archive(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    live_db = data / "sigma.db"
    con = sqlite3.connect(live_db)
    con.execute("create table t (id integer primary key, name text)")
    con.execute("insert into t(name) values ('old')")
    _apply_commercial_schema(con)
    con.execute(
        "insert into school_subscriptions"
        " (school_id, plan_code, status, starts_on, ends_on, max_users, max_students)"
        " values (1, 'standard', 'active', '2026-01-01', '2099-12-31', 50, 1000)"
    )
    con.commit(); con.close()
    media = data / "media"
    media.mkdir(); (media / "old.txt").write_text("old", encoding="utf-8")
    staged = data / "restore.zip"
    staged.write_bytes(archive.read_bytes())
    state = data / "restore_pending.json"
    state.write_text(json.dumps({"token": "tok", "archive": str(staged), "status": "pending_restart"}), encoding="utf-8")

    class E: pass
    e = E(); e.url = E(); e.url.database = str(live_db)
    monkeypatch.setattr(backup, "data_dir", lambda: data)
    monkeypatch.setattr(backup, "restore_state_path", lambda: state)
    monkeypatch.setattr(backup, "engine", e)
    monkeypatch.setattr(backup, "media_root", lambda: media)

    result = backup.apply_pending_restore()
    assert result["status"] == "applied"
    assert not state.exists()
    assert not staged.exists()
    con = sqlite3.connect(live_db)
    assert con.execute("select name from t").fetchone()[0] == "ok"
    # L'abonnement vivant survit à la restauration, il n'est pas écrasé par
    # celui (absent) de l'archive cliente.
    assert con.execute("select status from school_subscriptions").fetchone()[0] == "active"
    con.close()
    assert not (media / "old.txt").exists()


def test_validate_backup_rejects_path_traversal(tmp_path):
    db = tmp_path / "sigma.db"
    db.write_bytes(b"not sqlite")
    manifest = {"format": 2, "files": [{"path": "../escape.txt", "sha256": "x", "size": 1}]}
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../escape.txt", "x")
        z.writestr("sigma.db", b"x")
        z.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(ValueError, match="dangereux"):
        backup.validate_backup(archive)
