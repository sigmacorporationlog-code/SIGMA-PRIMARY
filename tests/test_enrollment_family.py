from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_enrollment_and_family_endpoints_present():
    src=(ROOT/'app/api/students.py').read_text(encoding='utf-8')
    for marker in ['/enrollments', '/enrollments/transfer', '/students/{student_id}/guardians', '/guardians/{guardian_id}']:
        assert marker in src
    assert 'students.transfer' in src
    assert 'Aucune inscription active à transférer' in src
    assert 'Ce responsable est déjà lié à l\'élève' in src

def test_student_model_preserves_historical_memberships():
    src=(ROOT/'app/models/students.py').read_text(encoding='utf-8')
    assert 'UniqueConstraint("student_id", "class_id", "academic_year_id"' in src
    assert 'left_at' in src
