from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_assessment_creation_binds_class_period_subject_to_tenant():
    text = (ROOT / "app/api/academic.py").read_text(encoding="utf-8")
    fn = text[text.index("def create_assessment"):text.index("@router.get(\"/assessments\"")]
    assert "_class_access(db, current_user, payload.class_id)" in fn
    assert "_period_access(db, current_user, payload.academic_period_id)" in fn
    assert "subject.school_id != cls.school_id" in fn
    assert "period.academic_year_id != cls.academic_year_id" in fn


def test_grade_upsert_rejects_foreign_or_non_member_students():
    text = (ROOT / "app/api/academic.py").read_text(encoding="utf-8")
    fn = text[text.index("def upsert_grades"):text.index("@router.post(\"/grades/transition\"")]
    assert "Student.school_id == current_user.school_id" in fn
    assert "student_id not in member_ids" in fn
