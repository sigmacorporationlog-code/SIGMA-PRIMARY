from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "api" / "evaluation.py"


def test_teacher_workspace_is_assignment_scoped():
    text = SRC.read_text(encoding="utf-8")
    marker = 'def teacher_workspace(class_id: int, academic_period_id: int'
    section = text[text.index(marker):]
    assert 'TeacherAssignment.teacher_id == current_user.id' in section
    assert 'TeacherAssignment.class_id == class_id' in section
    assert 'TeacherAssignment.academic_year_id == cls.academic_year_id' in section
    assert 'Classe non affectée à cet enseignant' in section


def test_teacher_portal_roster_already_requires_assignment():
    text = (ROOT / "app" / "services" / "teacher_portal.py").read_text(encoding="utf-8")
    assert 'TeacherAssignment.teacher_id == user.id' in text
    assert 'TeacherAssignment.class_id == class_id' in text
