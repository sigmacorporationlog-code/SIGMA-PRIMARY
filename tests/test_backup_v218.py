from app.services.backup import validate_backup
import hashlib, json, zipfile

def _archive(tmp_path, data=None):
    p = tmp_path / "backup.zip"
    import sqlite3
    db = tmp_path / "fixture.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE IF NOT EXISTS test(id INTEGER PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO test(value) VALUES ('SIGMA')")
    con.commit(); con.close()
    payload = db.read_bytes()
    manifest = {"format": 2, "created_at": "now", "files": [{"path": "sigma.db", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}]}
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("sigma.db", payload)
        z.writestr("manifest.json", json.dumps(manifest))
    return p

def test_backup_manifest_has_sha256_and_size(tmp_path):
    assert validate_backup(_archive(tmp_path, b"sqlite-test"))["format"] == 2

def test_backup_detects_tampering(tmp_path):
    p = _archive(tmp_path)
    q = tmp_path / "tampered.zip"
    with zipfile.ZipFile(p) as src, zipfile.ZipFile(q, "w") as dst:
        for info in src.infolist():
            dst.writestr(info, b"tampered" if info.filename == "sigma.db" else src.read(info.filename))
    try:
        validate_backup(q)
        assert False
    except ValueError as exc:
        assert "SHA-256" in str(exc) or "Taille incohérente" in str(exc)


def test_restore_backup_to_isolated_directory(tmp_path):
    from app.services.backup import restore_backup_to_directory
    archive = _archive(tmp_path, b"valid-sqlite-placeholder")
    # Remplace le placeholder par une vraie petite base SQLite.
    db = tmp_path / "real.db"
    import sqlite3
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO test(value) VALUES ('SIGMA')")
    con.commit(); con.close()
    p = tmp_path / "restoreable.zip"
    digest = hashlib.sha256(db.read_bytes()).hexdigest()
    manifest = {"format": 2, "app_version": "test", "created_at": "now", "files": [{"path": "sigma.db", "sha256": digest, "size": db.stat().st_size}]}
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(db, "sigma.db")
        z.writestr("manifest.json", json.dumps(manifest))
    target = tmp_path / "restored"
    result = restore_backup_to_directory(p, target)
    assert result["status"] == "restored"
    restored = sqlite3.connect(target / "sigma.db")
    assert restored.execute("SELECT value FROM test").fetchone()[0] == "SIGMA"
    restored.close()


def test_restore_rejects_non_empty_target(tmp_path):
    from app.services.backup import restore_backup_to_directory
    p = _archive(tmp_path, b"x")
    target = tmp_path / "target"
    target.mkdir()
    (target / "existing.txt").write_text("do not overwrite")
    try:
        restore_backup_to_directory(p, target)
        assert False
    except ValueError as exc:
        assert "vide" in str(exc)
