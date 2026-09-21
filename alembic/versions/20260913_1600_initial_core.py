"""SIGMA initial schema baseline. Creates the pre-V1.7 core schema.

This migration is intentionally based on the SIGMA V3 baseline schema rather
than the current ORM metadata so later migrations remain authoritative.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_1600"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(150), nullable=False),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_permissions_code", "permissions", ['code'], unique=True)

    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(50)),
        sa.Column("logo_path", sa.String(500)),
        sa.Column("address", sa.String(500)),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(255)),
        sa.Column("website", sa.String(255)),
        sa.Column("phone_secondary", sa.String(50)),
        sa.Column("official_stamp_path", sa.String(500)),
        sa.Column("ministry_name", sa.String(255), nullable=False, default='Ministère de l’Éducation de Base'),
        sa.Column("school_type", sa.String(100)),
        sa.Column("regime", sa.String(100)),
        sa.Column("language", sa.String(10), nullable=False, default='fr'),
        sa.Column("currency", sa.String(10), nullable=False, default='XAF'),
        sa.Column("grading_system", sa.String(50), nullable=False, default='20'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "academic_years",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("label", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "campuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "card_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("card_type", sa.String(30), nullable=False, default='student_id'),
        sa.Column("layout", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "honor_board_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "streams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("matricule", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("birth_date", sa.Date()),
        sa.Column("birth_place", sa.String(255)),
        sa.Column("sex", sa.String(1)),
        sa.Column("nationality", sa.String(100)),
        sa.Column("photo_path", sa.String(500)),
        sa.Column("address", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False, default='active'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.UniqueConstraint('school_id', 'matricule', name="uq_student_matricule_per_school"),
    )
    op.create_index("ix_students_matricule", "students", ['matricule'], unique=False)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("default_coefficient", sa.Float(), nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("photo_path", sa.String(500)),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, default=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )
    op.create_index("ix_users_email", "users", ['email'], unique=True)
    op.create_index("ix_users_username", "users", ['username'], unique=True)

    op.create_table(
        "academic_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, default=1),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_grade_entry_open", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("device", sa.String(255)),
    )

    op.create_table(
        "cash_register_closures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("closure_date", sa.Date(), nullable=False),
        sa.Column("total_receipts", sa.Float(), nullable=False),
        sa.Column("total_expenses", sa.Float(), nullable=False),
        sa.Column("net_balance", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id"), nullable=False),
        sa.Column("stream_id", sa.Integer(), sa.ForeignKey("streams.id")),
        sa.Column("campus_id", sa.Integer(), sa.ForeignKey("campuses.id")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("homeroom_teacher_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("capacity", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "delegations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("granted_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("granted_to_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "disciplinary_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reported_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluation_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("school_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("section", sa.String(20), nullable=False),
        sa.Column("cycle", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(30), nullable=False, default='2018'),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("spent_at", sa.Date(), nullable=False),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "fee_structures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id")),
        sa.Column("fee_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "guardians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(255)),
        sa.Column("address", sa.String(500)),
        sa.Column("can_pick_up_child", sa.Boolean(), nullable=False, default=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "id_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("card_templates.id"), nullable=False),
        sa.Column("holder_type", sa.String(20), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("card_number", sa.String(50), nullable=False),
        sa.Column("access_code", sa.String(100), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("expires_at", sa.Date()),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("revoked_reason", sa.Text()),
        sa.Column("print_count", sa.Integer(), nullable=False, default=0),
        sa.Column("last_printed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('card_number'),
    )

    op.create_table(
        "post_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('post_id', 'permission_id', 'scope', name="uq_post_permission_scope"),
    )

    op.create_table(
        "user_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'post_id', name="uq_user_post"),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_period_id", sa.Integer(), sa.ForeignKey("academic_periods.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("assessment_type", sa.String(50), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False, default=20.0),
        sa.Column("coefficient", sa.Float(), nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_justified", sa.Boolean(), nullable=False, default=False),
        sa.Column("justification_reason", sa.Text()),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "class_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("enrolled_at", sa.Date(), nullable=False),
        sa.Column("left_at", sa.Date()),
        sa.Column("enrollment_type", sa.String(30), nullable=False, default='inscription'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('student_id', 'class_id', 'academic_year_id', name="uq_membership_year"),
    )

    op.create_table(
        "evaluation_appreciation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("evaluation_frameworks.id"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("min_percent", sa.Float()),
        sa.Column("max_percent", sa.Float()),
        sa.Column("text_fr", sa.Text(), nullable=False),
        sa.Column("text_en", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, default=1),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('framework_id', 'code', name="uq_eval_appreciation_rule_code"),
    )

    op.create_table(
        "evaluation_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("evaluation_frameworks.id"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("weight", sa.Float()),
        sa.Column("display_order", sa.Integer(), nullable=False, default=1),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('framework_id', 'code', name="uq_eval_domain_code"),
    )

    op.create_table(
        "evaluation_period_closures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("academic_period_id", sa.Integer(), sa.ForeignKey("academic_periods.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default='closed'),
        sa.Column("closed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("published_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('class_id', 'academic_period_id', name="uq_eval_period_closure"),
    )

    op.create_table(
        "honor_board_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("honor_board_rules.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("academic_period_id", sa.Integer(), sa.ForeignKey("academic_periods.id"), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("rank", sa.Integer()),
        sa.Column("is_validated", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("fee_structure_id", sa.Integer(), sa.ForeignKey("fee_structures.id"), nullable=False),
        sa.Column("amount_due", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False, default=0.0),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(20), nullable=False, default='pending'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rating_scales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("evaluation_frameworks.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("min_percent", sa.Float()),
        sa.Column("max_percent", sa.Float()),
        sa.Column("description", sa.Text()),
        sa.Column("color", sa.String(20)),
        sa.Column("display_order", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('framework_id', 'code', name="uq_rating_scale_code"),
    )

    op.create_table(
        "report_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("academic_period_id", sa.Integer(), sa.ForeignKey("academic_periods.id"), nullable=False),
        sa.Column("general_average", sa.Float()),
        sa.Column("class_rank", sa.Integer()),
        sa.Column("class_size", sa.Integer()),
        sa.Column("appreciation", sa.Text()),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("file_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('student_id', 'academic_period_id', name="uq_report_card_per_student_period"),
    )

    op.create_table(
        "sms_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("sent_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_phone", sa.String(50), nullable=False),
        sa.Column("recipient_label", sa.String(255)),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id")),
        sa.Column("guardian_id", sa.Integer(), sa.ForeignKey("guardians.id")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("campaign_label", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False, default='pending'),
        sa.Column("provider_reference", sa.String(150)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "student_guardians",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("guardian_id", sa.Integer(), sa.ForeignKey("guardians.id"), nullable=False),
        sa.Column("is_primary_contact", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "teacher_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_year_id", sa.Integer(), sa.ForeignKey("academic_years.id"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("coefficient", sa.Float()),
        sa.Column("weekly_hours", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('academic_year_id', 'teacher_id', 'subject_id', 'class_id', name="uq_teacher_assignment"),
    )

    op.create_table(
        "evaluation_competencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("evaluation_domains.id"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('domain_id', 'code', name="uq_eval_comp_code"),
    )

    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("is_absent", sa.Boolean(), nullable=False, default=False),
        sa.Column("state", sa.String(20), nullable=False, default='draft'),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('assessment_id', 'student_id', name="uq_grade_per_student_assessment"),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("received_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, default=False),
        sa.Column("cancelled_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluation_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competency_id", sa.Integer(), sa.ForeignKey("evaluation_competencies.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("evaluation_mode", sa.String(30), nullable=False, default='observation'),
        sa.Column("max_score", sa.Float()),
        sa.Column("weight", sa.Float()),
        sa.Column("display_order", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('competency_id', 'code', name="uq_eval_criterion_code"),
    )

    op.create_table(
        "grade_state_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("grades.id"), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("from_state", sa.String(20)),
        sa.Column("to_state", sa.String(20), nullable=False),
        sa.Column("old_score", sa.Float()),
        sa.Column("new_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("receipt_number", sa.String(50), nullable=False),
        sa.Column("print_count", sa.Integer(), nullable=False, default=1),
        sa.Column("file_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('payment_id'),
        sa.UniqueConstraint('receipt_number'),
    )

    op.create_table(
        "evaluation_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_period_id", sa.Integer(), sa.ForeignKey("academic_periods.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id")),
        sa.Column("criterion_id", sa.Integer(), sa.ForeignKey("evaluation_criteria.id")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("assessment_type", sa.String(30), nullable=False, default='formative'),
        sa.Column("mode", sa.String(30), nullable=False, default='observation'),
        sa.Column("max_score", sa.Float()),
        sa.Column("coefficient", sa.Float(), nullable=False, default=1.0),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("activity_id", sa.Integer(), sa.ForeignKey("evaluation_activities.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("max_score", sa.Float()),
        sa.Column("rating_code", sa.String(20)),
        sa.Column("is_absent", sa.Boolean(), nullable=False, default=False),
        sa.Column("observation", sa.Text()),
        sa.Column("strengths", sa.Text()),
        sa.Column("needs_support", sa.Text()),
        sa.Column("state", sa.String(20), nullable=False, default='draft'),
        sa.Column("validated_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('activity_id', 'student_id', name="uq_eval_result_student_activity"),
    )

def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_activities")
    op.drop_table("receipts")
    op.drop_table("grade_state_history")
    op.drop_table("evaluation_criteria")
    op.drop_table("payments")
    op.drop_table("grades")
    op.drop_table("evaluation_competencies")
    op.drop_table("teacher_assignments")
    op.drop_table("student_guardians")
    op.drop_table("sms_logs")
    op.drop_table("report_cards")
    op.drop_table("rating_scales")
    op.drop_table("invoices")
    op.drop_table("honor_board_entries")
    op.drop_table("evaluation_period_closures")
    op.drop_table("evaluation_domains")
    op.drop_table("evaluation_appreciation_rules")
    op.drop_table("class_memberships")
    op.drop_table("attendance_records")
    op.drop_table("assessments")
    op.drop_table("user_posts")
    op.drop_table("post_permissions")
    op.drop_table("id_cards")
    op.drop_table("guardians")
    op.drop_table("fee_structures")
    op.drop_table("expenses")
    op.drop_table("evaluation_frameworks")
    op.drop_table("disciplinary_records")
    op.drop_table("delegations")
    op.drop_table("classes")
    op.drop_table("cash_register_closures")
    op.drop_table("audit_logs")
    op.drop_table("academic_periods")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("subjects")
    op.drop_index("ix_students_matricule", table_name="students")
    op.drop_table("students")
    op.drop_table("streams")
    op.drop_table("posts")
    op.drop_table("levels")
    op.drop_table("honor_board_rules")
    op.drop_table("card_templates")
    op.drop_table("campuses")
    op.drop_table("academic_years")
    op.drop_table("schools")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
    op.drop_table("organizations")
