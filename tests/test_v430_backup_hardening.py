import hashlib, json, sqlite3, zipfile
from pathlib import Path
import pytest

from app.services.backup import validate_backup, restore_backup_to_directory


def test_restore_endpoint_has_upload_limit():
    source = Path(__file__).resolve().parents[1] / "app/api/system.py"
    text = source.read_text(encoding="utf-8")
    assert "RESTORE_MAX_UPLOAD_BYTES" in text
    assert "status_code=413" in text


def make_db(tmp_path):
    db = tmp_path / "fixture.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE test(id INTEGER PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO test(value) VALUES ('SIGMA')")
    con.commit(); con.close()
    return db


def make_archive(tmp_path, members, manifest_files=None):
    p = tmp_path / "case.zip"
    if manifest_files is None:
        manifest_files = [{"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in members.items()]
    manifest = {"format": 2, "created_at": "now", "files": manifest_files}
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
        z.writestr("manifest.json", json.dumps(manifest))
    return p


def test_backup_rejects_undeclared_zip_member(tmp_path):
    db = make_db(tmp_path)
    data = db.read_bytes()
    p = make_archive(tmp_path, {"sigma.db": data, "unexpected.bin": b"x"}, [{"path": "sigma.db", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}])
    with pytest.raises(ValueError, match="non déclarées"):
        validate_backup(p)


def test_backup_rejects_duplicate_zip_member(tmp_path):
    db = make_db(tmp_path)
    data = db.read_bytes()
    p = tmp_path / "duplicate.zip"
    manifest = {"format": 2, "created_at": "now", "files": [{"path": "sigma.db", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}]}
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("sigma.db", data)
            z.writestr("sigma.db", data)
            z.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(ValueError, match="dupliquées"):
        validate_backup(p)


def test_backup_rejects_path_traversal_in_manifest(tmp_path):
    db = make_db(tmp_path)
    data = db.read_bytes()
    files = [{"path": "../sigma.db", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}]
    p = make_archive(tmp_path, {"sigma.db": data}, files)
    with pytest.raises(ValueError, match="dangereux"):
        validate_backup(p)


def test_backup_rejects_invalid_sqlite(tmp_path):
    p = make_archive(tmp_path, {"sigma.db": b"not a sqlite database"})
    with pytest.raises(ValueError, match="SQLite"):
        validate_backup(p)


def test_restore_rejects_non_empty_target_before_mutation(tmp_path):
    db = make_db(tmp_path)
    data = db.read_bytes()
    p = make_archive(tmp_path, {"sigma.db": data})
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("KEEP")
    with pytest.raises(ValueError, match="vide"):
        restore_backup_to_directory(p, target)
    assert sentinel.read_text(encoding="utf-8") == "KEEP"
