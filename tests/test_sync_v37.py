from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_v37_sync_health_contract_and_local_state():
    api = (ROOT / 'app/api/sync.py').read_text(encoding='utf-8')
    model = (ROOT / 'app/models/sync.py').read_text(encoding='utf-8')
    client = (ROOT / 'app/services/sync_client.py').read_text(encoding='utf-8')
    offline = (ROOT / 'app/services/offline_client.py').read_text(encoding='utf-8')
    migration = (ROOT / 'alembic/versions/20260914_3700_sync_v3.py').read_text(encoding='utf-8')
    assert 'last_sync_at' in model
    assert 'last_sync_status' in model
    assert 'last_sync_error' in model
    assert '@router.get("/devices/{device_id}/state")' in api
    assert '"healthy"' in api
    assert 'set_sync_state' in offline
    assert 'sync_state' in offline
    assert 'set_sync_state("offline"' in client
    assert '20260914_3700' in migration
    assert '20260914_3500' in migration
