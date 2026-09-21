from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import apply_business_mutation


from tests._sync_fakes import FakeDB  # noqa: E402


def test_v20_offline_student_create_assigns_server_identity():
    db = FakeDB()
    op = SimpleNamespace(
        operation_type='create', entity_type='student', entity_id='client-student-001', school_id=1, device_id='device-001',
        payload={'matricule':'OFF-001','first_name':'Grace','last_name':'Manga'}
    )
    result = apply_business_mutation(db, op, 0)
    assert result['operation_type'] == 'create'
    assert result['entity_id'] == 101
    assert result['client_entity_id'] == 'client-student-001'
    assert any(obj.__class__.__name__ == 'SyncEntityIdentity' for obj in db.added)


def test_v20_rejects_missing_student_identity_fields():
    db = FakeDB()
    op = SimpleNamespace(operation_type='create', entity_type='student', entity_id='client-student-002', school_id=1, device_id='device-001', payload={'first_name':'A'})
    try:
        apply_business_mutation(db, op, 0)
    except ValueError as exc:
        assert 'obligatoires' in str(exc)
    else:
        raise AssertionError('Une création élève sans matricule doit être refusée')


def test_v20_create_identity_is_required_and_documented():
    src = (ROOT / 'app/models/sync.py').read_text(encoding='utf8')
    api = (ROOT / 'app/api/sync.py').read_text(encoding='utf8')
    cfg = (ROOT / 'app/core/config.py').read_text(encoding='utf8')
    release = (ROOT / 'docs/RELEASE_2.0.md').read_text(encoding='utf8')
    assert 'class SyncEntityIdentity' in src
    assert 'apply_business_mutation' in api
    assert 'APP_VERSION: str' in cfg
    assert 'client_entity_id' in release
