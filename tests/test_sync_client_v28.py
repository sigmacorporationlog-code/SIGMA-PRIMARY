from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.offline_client import OfflineSyncStore
from app.services.sync_client import SyncClientEngine, SyncNetworkError


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.pushed = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path.startswith('/api/sync/compatibility?'):
            return {'compatible': True, 'server_version': '2.26.0-primary-commercial'}
        if path == '/api/sync/devices/register':
            return {'device_id': body['device_id'], 'status': 'online'}
        if path == '/api/sync/devices/heartbeat':
            return {'status': 'ok'}
        if path == '/api/sync/push':
            self.pushed.extend(body)
            return {'accepted': len(body), 'items': [
                {'operation_id': x['operation_id'], 'status': 'pending', 'server_version': x['base_version']}
                for x in body
            ]}
        if path == '/api/sync/apply-batch':
            return {'items': [
                {'operation_id': x, 'status': 'applied', 'server_version': 1,
                 'mutation': {'entity_type': 'student', 'entity_id': 77, 'operation_type': 'create'}}
                for x in body
            ]}
        if path.startswith('/api/sync/pull?'):
            return {'items': [{
                'id': 10, 'operation_id': 'remote-001', 'device_id': 'device-0002',
                'entity_type': 'student', 'entity_id': 'remote-student-1',
                'operation_type': 'update', 'server_version': 2,
                'payload': {'last_name': 'Offline'}
            }], 'next_id': 10}
        if path == '/api/sync/ack':
            return {'acknowledged': len(body['operation_ids'])}
        raise AssertionError(path)


def test_v28_full_sync_cycle_and_local_cache(tmp_path):
    store = OfflineSyncStore(tmp_path / 'client.sqlite3', 'device-0001', 1)
    op = store.enqueue('student', 'student-off-001', 'create', 0, {'first_name': 'A'})
    transport = FakeTransport()
    engine = SyncClientEngine(store, transport)
    engine.register('Poste direction')
    result = engine.sync_once()
    assert result.status == 'synchronized'
    assert store.summary()['applied'] == 1
    assert store.resolve_identity('student', 'student-off-001') == 77
    cached = engine.cache.get('student', 'remote-student-1')
    assert cached['payload']['last_name'] == 'Offline'
    assert store.last_pull_id() == 10
    assert any(x[1] == '/api/sync/apply-batch' for x in transport.calls)
    assert any(x[1] == '/api/sync/ack' for x in transport.calls)


def test_v28_network_failure_preserves_outbox(tmp_path):
    class OfflineTransport:
        def request(self, method, path, body=None):
            raise SyncNetworkError('network down')
    store = OfflineSyncStore(tmp_path / 'client.sqlite3', 'device-0001', 1)
    store.enqueue('student', 'student-off-001', 'create', 0, {'first_name': 'A'})
    result = SyncClientEngine(store, OfflineTransport()).sync_once()
    assert result.status == 'offline'
    assert len(store.pending()) == 1
