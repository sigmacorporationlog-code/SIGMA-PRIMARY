from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import apply_business_mutation
from app.models.students import Student, SchoolClass, ClassMembership
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
                # is_(None) and other SQL expressions are not needed by this fake.
                pass
        self.rows = rows
        return self
    def first(self): return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, mapping=None):
        self.added=[]; self.mapping=mapping or {}
    def query(self, model):
        return FakeQuery(self.mapping.get(model, []))
    def add(self, obj):
        if getattr(obj,'id',None) is None: obj.id=901
        self.added.append(obj)
    def flush(self): pass


def test_v21_offline_enrollment_resolves_student_client_identity():
    student = Student(id=77, school_id=1, matricule='OFF-001', first_name='A', last_name='B')
    school_class = SchoolClass(id=12, school_id=1, academic_year_id=3, level_id=1, name='SIL A')
    identity = SyncEntityIdentity(school_id=1, device_id='dev-001', entity_type='student', client_entity_id='client-student-001', server_entity_id=77)
    db=FakeDB({SyncEntityIdentity:[identity], Student:[student], SchoolClass:[school_class], ClassMembership:[]})
    op=SimpleNamespace(operation_type='create', entity_type='class_membership', entity_id='client-membership-001', school_id=1, device_id='dev-001', payload={'student_entity_id':'client-student-001','class_id':12,'academic_year_id':3,'enrolled_at':'2026-09-01','enrollment_type':'inscription'})
    result=apply_business_mutation(db, op, 0)
    assert result['operation_type']=='create'
    assert any(isinstance(x, ClassMembership) and x.student_id==77 and x.class_id==12 for x in db.added)


def test_v21_rejects_unknown_student_identity():
    db=FakeDB({SyncEntityIdentity:[]})
    op=SimpleNamespace(operation_type='create', entity_type='class_membership', entity_id='client-membership-002', school_id=1, device_id='dev-001', payload={'student_entity_id':'missing-student','class_id':12,'academic_year_id':3})
    try: apply_business_mutation(db, op, 0)
    except ValueError as exc: assert 'Élève inconnu' in str(exc)
    else: raise AssertionError('Une inscription ne doit pas être créée sans élève synchronisé')


def test_v21_rejects_existing_active_enrollment():
    student=Student(id=77, school_id=1, matricule='OFF-001', first_name='A', last_name='B')
    school_class=SchoolClass(id=12, school_id=1, academic_year_id=3, level_id=1, name='SIL A')
    identity=SyncEntityIdentity(school_id=1, device_id='dev-001', entity_type='student', client_entity_id='client-student-001', server_entity_id=77)
    existing=ClassMembership(id=44, student_id=77, class_id=9, academic_year_id=3, enrolled_at=__import__('datetime').date(2026,9,1), left_at=None, enrollment_type='inscription')
    db=FakeDB({SyncEntityIdentity:[identity], Student:[student], SchoolClass:[school_class], ClassMembership:[existing]})
    op=SimpleNamespace(operation_type='create', entity_type='class_membership', entity_id='client-membership-003', school_id=1, device_id='dev-001', payload={'student_entity_id':'client-student-001','class_id':12,'academic_year_id':3})
    try: apply_business_mutation(db, op, 0)
    except ValueError as exc: assert 'inscription active' in str(exc)
    else: raise AssertionError('Deux inscriptions actives la même année doivent être refusées')
