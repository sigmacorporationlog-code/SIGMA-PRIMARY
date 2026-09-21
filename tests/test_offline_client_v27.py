from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.offline_client import OfflineSyncStore


def test_v27_persistent_outbox_and_idempotence(tmp_path):
    db = tmp_path / 'client.sqlite3'
    store = OfflineSyncStore(db, 'device-0001', 1)
    op = store.enqueue('student', 'student-off-001', 'create', 0, {'first_name': 'A'})
    assert len(store.pending()) == 1
    assert store.enqueue('student', 'student-off-001', 'create', 0, {'first_name': 'A'}, op) == op
    assert len(store.pending()) == 1
    reopened = OfflineSyncStore(db, 'device-0001', 1)
    assert reopened.pending()[0]['operation_id'] == op


def test_v27_result_conflict_and_resolution(tmp_path):
    store = OfflineSyncStore(tmp_path / 'client.sqlite3', 'device-0001', 1)
    op = store.enqueue('grade', 'grade-off-001', 'update', 2, {'score': 15})
    store.mark_result(op, 'conflict', server_version=3, error='version')
    assert len(store.conflicts()) == 1
    store.resolve_conflict(op, 'retry')
    assert store.pending()[0]['operation_id'] == op
    assert store.conflicts() == []


def test_v27_pull_is_durable_and_idempotent(tmp_path):
    store = OfflineSyncStore(tmp_path / 'client.sqlite3', 'device-0001', 1)
    items = [{'id': 8, 'operation_id': 'server-op-001', 'device_id': 'device-0002',
              'entity_type': 'student', 'entity_id': '77', 'operation_type': 'update',
              'server_version': 4, 'payload': {'last_name': 'N'}}]
    assert store.ingest_pull(items, next_id=8) == 1
    assert store.ingest_pull(items, next_id=8) == 0
    assert len(store.inbox()) == 1
    assert store.last_pull_id() == 8


def test_v27_identity_and_summary(tmp_path):
    store = OfflineSyncStore(tmp_path / 'client.sqlite3', 'device-0001', 1)
    store.set_identity('student', 'student-off-001', 77)
    assert store.resolve_identity('student', 'student-off-001') == 77
    op = store.enqueue('student', 'student-off-002', 'create', 0, {'first_name': 'B'})
    store.mark_result(op, 'applied', 1)
    summary = store.summary()
    assert summary['applied'] == 1
    assert summary['pending'] == 0
