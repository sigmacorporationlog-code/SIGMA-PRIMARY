from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_academic_configuration_endpoints_present():
    src = (ROOT / "app/api/academic.py").read_text(encoding="utf-8")
    for route in ["/teachers", "/teacher-assignments"]:
        assert f'"{route}"' in src
    assert "IntegrityError" in src
    assert "Cette affectation enseignant/matière/classe existe déjà" in src
    assert "ressources doivent appartenir au même établissement" in src


def test_academic_page_exposes_configuration_workflow():
    html = (ROOT / "static/academic.html").read_text(encoding="utf-8")
    for marker in [
        "data-tab=\"configuration\"",
        "createAcademicClass()",
        "createTeacherAssignment()",
        "/api/teachers?school_id=",
        "/api/teacher-assignments?academic_year_id=",
    ]:
        assert marker in html


def test_subject_endpoints_are_school_scoped():
    src = (ROOT / "app/api/academic.py").read_text(encoding="utf-8")
    assert 'payload.school_id != current_user.school_id' in src
    assert 'school_id != current_user.school_id' in src
    assert 'Subject.is_active.is_(True)' in src
