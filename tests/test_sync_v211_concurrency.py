from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def test_conflict_resolution_model_and_migration():
    model=(Path(__file__).parents[1]/"app/models/sync.py").read_text(encoding="utf-8")
    mig=(Path(__file__).parents[1]/"alembic/versions/20260913_2600_sync_v26.py").read_text(encoding="utf-8")
    api=(Path(__file__).parents[1]/"app/api/sync.py").read_text(encoding="utf-8")
    assert "resolution" in model and "resolved_by_id" in model
    assert "20260913_2600" in mig and "20260913_2500" in mig
    assert "/conflicts/{operation_id}/resolve" in api
    assert "rebase" in api and "discard" in api
