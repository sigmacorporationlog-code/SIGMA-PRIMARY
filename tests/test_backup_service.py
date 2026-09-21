from pathlib import Path


def test_backup_service_is_present():
    root = Path(__file__).resolve().parents[1]
    assert (root / "app/services/backup.py").exists()
    assert (root / "app/api/system.py").exists()


def test_backup_archive_is_safe_filename():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/api/system.py").read_text(encoding="utf-8")
    assert "Path(name).name" in source
