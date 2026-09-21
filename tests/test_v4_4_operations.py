from pathlib import Path
import json
import zipfile

from app.services import backup, operations


def test_operations_overview_has_core_sections():
    result = operations.system_overview()
    assert "application" in result
    assert "storage" in result
    assert "backups" in result
    assert "upgrade" in result


def test_prune_backups_keeps_configured_count(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "backup_root", lambda: tmp_path)
    import sqlite3, hashlib
    for i in range(4):
        p = tmp_path / f"SIGMA_backup_{i:04d}.zip"
        db = tmp_path / f"fixture_{i}.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE test(id INTEGER PRIMARY KEY)")
        con.commit(); con.close()
        data = db.read_bytes()
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("sigma.db", data)
            manifest = {"format": 2, "created_at": "2026-01-01T00:00:00", "files": [{"path": "sigma.db", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}]}
            zf.writestr("manifest.json", json.dumps(manifest))
    result = backup.prune_backups(2)
    assert result["removed_count"] == 2
    assert len(list(tmp_path.glob("SIGMA_backup_*.zip"))) == 2


def test_release_package_validation(tmp_path):
    package = tmp_path / "sigma-release.zip"
    with zipfile.ZipFile(package, "w") as zf:
        zf.writestr("app/main.py", "print('sigma')")
        zf.writestr("release.json", json.dumps({"version": "4.4.0"}))
    result = operations.prepare_release_manifest(package)
    assert result["status"] == "validated"
    assert result["manifest"]["version"] == "4.4.0"
    assert len(result["sha256"]) == 64
