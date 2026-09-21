"""SIGMA V4.46 hardening: indexes for high-volume school workflows."""
from alembic import op

revision = "20260920_6000"
down_revision = "20260919_5900"
branch_labels = None
depends_on = None


INDEXES = [
    ("ix_students_school_status", "students", ["school_id", "status"]),
    ("ix_students_school_name", "students", ["school_id", "last_name", "first_name"]),
    ("ix_memberships_class_active", "class_memberships", ["class_id", "left_at"]),
    ("ix_memberships_student_year", "class_memberships", ["student_id", "academic_year_id"]),
    ("ix_assessments_period_class", "assessments", ["academic_period_id", "class_id", "is_active"]),
    ("ix_assessments_subject_class_period", "assessments", ["subject_id", "class_id", "academic_period_id"]),
    ("ix_grades_assessment_student", "grades", ["assessment_id", "student_id"]),
    ("ix_payments_invoice_cancelled", "payments", ["invoice_id", "is_cancelled"]),
    ("ix_payments_student_paid_at", "payments", ["student_id", "paid_at"]),
    ("ix_invoices_student_year_status", "invoices", ["student_id", "academic_year_id", "status"]),
    ("ix_attendance_class_date", "attendance_records", ["class_id", "date"]),
]


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade():
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
