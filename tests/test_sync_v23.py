from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sync import apply_business_mutation
from app.models.academic import Grade, Assessment
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
                pass
        self.rows = rows
        return self
    def first(self): return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, mapping=None): self.added=[]; self.mapping=mapping or {}
    def query(self, model): return FakeQuery(self.mapping.get(model, []))
    def add(self, obj):
        if getattr(obj, 'id', None) is None: obj.id=1201
        self.added.append(obj)
    def flush(self): pass


def grade_context():
    student = Student(id=77, school_id=1, matricule='OFF-001', first_name='A', last_name='B')
    school_class = SchoolClass(id=12, school_id=1, academic_year_id=3, level_id=1, name='SIL A')
    assessment = Assessment(id=55, academic_period_id=8, subject_id=9, class_id=12, created_by_id=4, name='Contrôle', assessment_type='devoir', max_score=20, coefficient=1)
    membership = ClassMembership(id=88, student_id=77, class_id=12, academic_year_id=3, enrolled_at=__import__('datetime').date(2026,9,1), left_at=None, enrollment_type='inscription')
    return {Assessment:[assessment], Student:[student], SchoolClass:[school_class], ClassMembership:[membership], SyncEntityIdentity:[] }


def test_v23_offline_grade_create_for_existing_assessment_and_student():
    db=FakeDB(grade_context())
    op=SimpleNamespace(operation_type='create', entity_type='grade', entity_id='client-grade-001', school_id=1, device_id='dev-001', payload={
        'assessment_id':55, 'student_id':77, 'score':15.5, 'is_absent':False, 'state':'draft', 'comment':'Bien'
    })
    result=apply_business_mutation(db, op, 0)
    assert result['operation_type']=='create'
    assert any(isinstance(x, Grade) and x.student_id==77 and x.assessment_id==55 and x.score==15.5 for x in db.added)
    assert any(isinstance(x, SyncEntityIdentity) and x.entity_type=='grade' for x in db.added)


def test_v23_offline_grade_resolves_student_client_identity():
    mapping=grade_context()
    mapping[SyncEntityIdentity]=[SyncEntityIdentity(school_id=1, device_id='dev-001', entity_type='student', client_entity_id='client-student-001', server_entity_id=77)]
    db=FakeDB(mapping)
    op=SimpleNamespace(operation_type='create', entity_type='grade', entity_id='client-grade-002', school_id=1, device_id='dev-001', payload={
        'assessment_id':55, 'student_entity_id':'client-student-001', 'score':12, 'is_absent':False
    })
    result=apply_business_mutation(db, op, 0)
    assert result['entity_id']==1201
    grade=next(x for x in db.added if isinstance(x, Grade))
    assert grade.student_id==77


def test_v23_grade_rejects_student_not_enrolled_in_assessment_class():
    mapping=grade_context()
    mapping[ClassMembership]=[]
    db=FakeDB(mapping)
    op=SimpleNamespace(operation_type='create', entity_type='grade', entity_id='client-grade-003', school_id=1, device_id='dev-001', payload={'assessment_id':55,'student_id':77,'score':10})
    try: apply_business_mutation(db, op, 0)
    except ValueError as exc: assert 'inscrit' in str(exc)
    else: raise AssertionError('Une note ne doit pas être créée pour un élève hors de la classe')


def test_v23_grade_rejects_duplicate_and_locked_mutation():
    mapping=grade_context()
    mapping[Grade]=[Grade(id=99, assessment_id=55, student_id=77, score=14, state='locked', is_absent=False)]
    db=FakeDB(mapping)
    op=SimpleNamespace(operation_type='create', entity_type='grade', entity_id='client-grade-004', school_id=1, device_id='dev-001', payload={'assessment_id':55,'student_id':77,'score':16})
    try: apply_business_mutation(db, op, 0)
    except ValueError as exc: assert 'existe déjà' in str(exc)
    else: raise AssertionError('Une note dupliquée doit être refusée')


def test_v23_sync_permission_routes_grade_to_academic_grades_enter():
    src=(ROOT/'app/api/sync.py').read_text(encoding='utf8')
    assert 'academic.grades.enter' in src
    assert '_sync_permission_allowed(db, current_user, item.entity_type, item.operation_type, item.payload)' in src


def grade_transition_context(state='draft', closure_rows=None):
    mapping = grade_context()
    mapping[Grade] = [Grade(id=99, assessment_id=55, student_id=77, score=14, state=state, is_absent=False)]
    from app.models.evaluation import EvaluationPeriodClosure
    mapping[EvaluationPeriodClosure] = closure_rows or []
    return mapping


def test_v24_grade_transition_is_sequential_and_audited():
    db = FakeDB(grade_transition_context('draft'))
    op = SimpleNamespace(operation_type='transition', entity_type='grade', entity_id='99', school_id=1,
                         device_id='dev-001', user_id=7, payload={'to_state': 'submitted'})
    result = apply_business_mutation(db, op, 0)
    assert result['from_state'] == 'draft'
    assert result['to_state'] == 'submitted'
    grade = db.mapping[Grade][0]
    assert grade.state == 'submitted'
    assert any(getattr(x, 'from_state', None) == 'draft' and getattr(x, 'to_state', None) == 'submitted' for x in db.added)


def test_v24_grade_transition_rejects_skipping_state():
    db = FakeDB(grade_transition_context('draft'))
    op = SimpleNamespace(operation_type='transition', entity_type='grade', entity_id='99', school_id=1,
                         device_id='dev-001', user_id=7, payload={'to_state': 'validated'})
    try:
        apply_business_mutation(db, op, 0)
    except ValueError as exc:
        assert 'Transition interdite' in str(exc)
    else:
        raise AssertionError('Une transition draft -> validated doit être refusée')


def test_v24_grade_transition_rejects_closed_period():
    from app.models.evaluation import EvaluationPeriodClosure
    closure = EvaluationPeriodClosure(id=1, class_id=12, academic_period_id=8, status='closed', closed_by_id=7)
    db = FakeDB(grade_transition_context('submitted', [closure]))
    op = SimpleNamespace(operation_type='transition', entity_type='grade', entity_id='99', school_id=1,
                         device_id='dev-001', user_id=7, payload={'to_state': 'checked'})
    try:
        apply_business_mutation(db, op, 0)
    except ValueError as exc:
        assert 'clôturée' in str(exc)
    else:
        raise AssertionError('Une période clôturée doit bloquer une transition synchronisée')


def test_v24_grade_update_cannot_change_state_directly():
    db = FakeDB(grade_transition_context('submitted'))
    op = SimpleNamespace(operation_type='update', entity_type='grade', entity_id='99', school_id=1,
                         device_id='dev-001', user_id=7, payload={'state': 'checked'})
    try:
        apply_business_mutation(db, op, 0)
    except ValueError as exc:
        assert 'opération transition' in str(exc)
    else:
        raise AssertionError('Le changement d’état doit utiliser une opération transition')
