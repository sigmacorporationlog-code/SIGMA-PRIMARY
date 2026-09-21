from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import apply_business_mutation
from app.models.students import Student, Guardian, StudentGuardian
from app.models.sync import SyncEntityIdentity


class FakeQuery:
    def __init__(self, rows=None): self.rows = rows or []
    def filter(self, *criteria, **kwargs):
        rows = self.rows
        for criterion in criteria:
            try:
                key = criterion.left.key
                value = criterion.right.value
                rows = [row for row in rows if getattr(row, key, None) == value]
            except Exception:
                pass
        self.rows = rows
        return self
    def first(self): return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, mapping=None): self.added=[]; self.mapping=mapping or {}
    def query(self, model): return FakeQuery(self.mapping.get(model, []))
    def add(self, obj):
        if getattr(obj, 'id', None) is None: obj.id=1401
        self.added.append(obj)
    def flush(self): pass


def test_v25_student_guardian_resolves_both_client_identities():
    student = Student(id=77, school_id=1, matricule='OFF-001', first_name='A', last_name='B')
    guardian = Guardian(id=88, school_id=1, first_name='Parent', last_name='A', relationship_type='père', phone='690000000')
    identities = [
        SyncEntityIdentity(school_id=1, device_id='dev-001', entity_type='student', client_entity_id='student-off-001', server_entity_id=77),
        SyncEntityIdentity(school_id=1, device_id='dev-001', entity_type='guardian', client_entity_id='guardian-off-001', server_entity_id=88),
    ]
    db = FakeDB({Student:[student], Guardian:[guardian], StudentGuardian:[], SyncEntityIdentity:identities})
    op = SimpleNamespace(operation_type='create', entity_type='student_guardian', entity_id='link-off-001', school_id=1, device_id='dev-001', payload={
        'student_entity_id':'student-off-001', 'guardian_entity_id':'guardian-off-001', 'is_primary_contact':True
    })
    result = apply_business_mutation(db, op, 0)
    link = next(x for x in db.added if isinstance(x, StudentGuardian))
    assert result['operation_type'] == 'create'
    assert link.student_id == 77 and link.guardian_id == 88 and link.is_primary_contact is True


def test_v25_student_guardian_rejects_unknown_identity():
    student = Student(id=77, school_id=1, matricule='OFF-001', first_name='A', last_name='B')
    db = FakeDB({Student:[student], Guardian:[], StudentGuardian:[], SyncEntityIdentity:[]})
    op = SimpleNamespace(operation_type='create', entity_type='student_guardian', entity_id='link-off-002', school_id=1, device_id='dev-001', payload={
        'student_entity_id':'missing-student', 'guardian_entity_id':'missing-guardian'
    })
    try:
        apply_business_mutation(db, op, 0)
    except ValueError as exc:
        assert 'Identité client inconnue' in str(exc)
    else:
        raise AssertionError('Une identité client absente doit être refusée')


def test_v25_api_exposes_batch_and_queue_recovery():
    src=(ROOT/'app/api/sync.py').read_text(encoding='utf8')
    assert '@router.post("/apply-batch")' in src
    assert '@router.get("/devices/{device_id}/queue")' in src
    assert 'validate_operation_type(item.operation_type)' in src
    assert 'student_guardian' in src


def test_v25_version_and_migration():
    config=(ROOT/'app/core/config.py').read_text(encoding='utf8')
    migration=(ROOT/'alembic/versions/20260913_2500_sync_v25.py').read_text(encoding='utf8')
    assert 'APP_VERSION: str' in config
    assert 'down_revision = "20260913_2400"' in migration
