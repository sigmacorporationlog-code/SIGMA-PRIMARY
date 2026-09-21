from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACADEMIC = (ROOT / 'app/api/academic.py').read_text(encoding="utf-8")
OFFLINE = (ROOT / 'static/assets/sigma-offline.js').read_text(encoding="utf-8")


def test_grade_read_exposes_sync_version():
    assert '"sync_version":' in ACADEMIC
    assert 'SyncEntityVersion.entity_type == "grade"' in ACADEMIC


def test_normal_grade_upsert_advances_sync_version():
    assert 'version.version += 1' in ACADEMIC
    assert 'entity_type="grade"' in ACADEMIC


def test_normal_grade_transition_advances_sync_version():
    assert ACADEMIC.count('version.version += 1') >= 2


def test_browser_offline_flush_applies_structured_sync_operations():
    assert 'const VERSION = 3;' in OFFLINE
    assert "createObjectStore('conflicts'" in OFFLINE
    assert 'ensureSyncDevice' in OFFLINE
    assert "item.kind === 'sync_operation'" in OFFLINE
    assert "'/api/sync/push'" in OFFLINE
    assert "'/api/sync/apply-batch'" in OFFLINE


def test_browser_grade_queue_uses_create_or_update_with_base_version():
    assert "const operationType = row.result_id != null ? 'update' : 'create'" in OFFLINE
    assert "base_version:Number(row.sync_version || 0)" in OFFLINE
    assert "entity_type:'evaluation_result'" in OFFLINE
