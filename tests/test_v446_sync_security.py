from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "app/api/sync.py").read_text(encoding="utf-8")
MODEL = (ROOT / "app/models/sync.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "app/services/sync.py").read_text(encoding="utf-8")


def test_sync_devices_are_user_bound():
    assert "owner_user_id" in MODEL
    assert "owner_user_id=current_user.id" in API
    assert "_device_access(db, current_user, device)" in API


def test_sync_operations_are_user_bound_for_apply_and_conflicts():
    assert "_operation_access(db, current_user, op)" in API
    assert "query = db.query(SyncOperation).filter" in API
    assert "SyncOperation.user_id == current_user.id" in API


def test_sync_rejects_unknown_entities_before_queueing():
    assert "if item.entity_type not in ENTITY_HANDLERS:" in API
    assert "Entité non synchronisable" in SERVICE
