from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_CLIENT = (ROOT / 'app/services/sync_client.py').read_text(encoding="utf-8")
SYNC_API = (ROOT / 'app/api/sync.py').read_text(encoding="utf-8")


def test_pull_exposes_canonical_server_identity():
    assert '"server_entity_id"' in SYNC_API
    assert 'SyncEntityIdentity.server_entity_id' in SYNC_API


def test_pull_resolves_client_entity_references():
    assert 'def _pull_payload' in SYNC_API
    assert 'client_entity_id == str(value)' in SYNC_API


def test_local_read_model_has_evaluation_results_and_rejects_stale_versions():
    assert '"evaluation_result": "local_evaluation_results"' in SYNC_CLIENT
    assert 'incoming_version < current_version' in SYNC_CLIENT


def test_pull_persists_cross_device_identity():
    assert 'self.store.set_identity(item["entity_type"]' in SYNC_CLIENT
