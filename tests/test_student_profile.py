from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_student_profile_endpoint_is_consolidated_and_school_scoped():
    src=(ROOT/'app/api/students.py').read_text(encoding='utf-8')
    assert '/students/{student_id}/profile' in src
    assert 'student.school_id != current_user.school_id' in src
    assert 'enrollment_history' in src
    assert 'primary_guardian' in src

def test_students_ui_exposes_profile_action():
    src=(ROOT/'static/students.html').read_text(encoding='utf-8')
    assert 'openProfile(${s.id})' in src
    assert '/api/students/${id}/profile' in src
    assert 'Historique scolaire' in src
