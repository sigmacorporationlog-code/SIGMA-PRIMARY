from tests.test_v4_17_parent_teacher import setup_db
from app.services.parent_portal import child_mobile_summary, child_invoices
from app.services.teacher_portal import teacher_class_roster


def test_parent_mobile_summary_is_compact_and_scoped():
    db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject = setup_db()
    data = child_mobile_summary(db, guardian, student)
    assert data['student']['id'] == student.id
    assert 'recent_grades' in data
    assert 'report_cards' not in data


def test_parent_invoices_only_for_linked_child():
    db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject = setup_db()
    assert child_invoices(db, guardian, other) == []


def test_teacher_roster_only_for_assigned_class():
    db, school, year, period, parent_user, teacher, guardian, student, other, klass, subject = setup_db()
    data = teacher_class_roster(db, teacher, klass.id)
    assert data['class']['name'] == '6e A'
    assert data['students'][0]['matricule'] == 'S-001'
    assert teacher_class_roster(db, teacher, 999)['students'] == []
