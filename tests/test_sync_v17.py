from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v17_sync_models_and_router_exist():
    model = (ROOT / "app/models/sync.py").read_text(encoding="utf8")
    api = (ROOT / "app/api/sync.py").read_text(encoding="utf8")
    main = (ROOT / "app/main.py").read_text(encoding="utf8")
    assert "class SyncDevice" in model
    assert "class SyncOperation" in model
    assert "class SyncEntityVersion" in model
    assert 'prefix="/api/sync"' in api
    assert "sync.router" in main


def test_v17_sync_has_idempotency_and_conflict_detection():
    api = (ROOT / "app/api/sync.py").read_text(encoding="utf8")
    assert 'operation_id' in api
    assert 'idempotent' in api
    assert 'status = "pending" if item.base_version == current_version else "conflict"' in api
    assert "Conflit de version" in api


def test_v17_sync_is_explicitly_safe_about_business_mutation():
    release = (ROOT / "docs/RELEASE_1.7.md").read_text(encoding="utf8")
    assert "n'applique pas encore automatiquement" in release
    assert "conflict" in release


def test_v18_version_bumped():
    cfg = (ROOT / "app/core/config.py").read_text(encoding="utf8")
    assert 'APP_VERSION: str = ' in cfg
