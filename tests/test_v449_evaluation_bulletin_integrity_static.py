from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'app' / 'api' / 'evaluation.py'


def _tree():
    return ast.parse(SRC.read_text(encoding='utf-8'))


def test_background_bulletin_worker_does_not_use_unbound_school_before_context_resolution():
    text = SRC.read_text(encoding='utf-8')
    assert '_SystemUser(school.id)' not in text
    assert 'cls_obj = db.get(SchoolClass, class_id)' in text
    assert '_SystemUser(cls_obj.school_id)' in text


def test_activities_endpoint_imports_teacher_assignment_before_filtering():
    text = SRC.read_text(encoding='utf-8')
    assert 'from app.models.academic import TeacherAssignment' in text
    assert 'db.query(TeacherAssignment).filter' in text


def test_bulletin_preview_validates_period_framework_and_optional_class():
    text = SRC.read_text(encoding='utf-8')
    assert 'period = db.get(AcademicPeriod, academic_period_id)' in text
    assert 'period.academic_year_id != framework.school_year_id' in text
    assert 'L\'élève n\'est pas inscrit dans cette classe pour cette année' in text


def test_evaluation_module_has_no_syntax_error():
    ast.parse(SRC.read_text(encoding='utf-8'))
