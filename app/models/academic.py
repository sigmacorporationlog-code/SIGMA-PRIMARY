from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Boolean, Text, UniqueConstraint, JSON, Numeric, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Subject(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    default_coefficient: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("1.0"), nullable=False)


class TeacherAssignment(Base, TimestampMixin):
    """Affectation d'un enseignant à une matière, dans une classe, pour une année."""

    __tablename__ = "teacher_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    coefficient: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    weekly_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint("academic_year_id", "teacher_id", "subject_id", "class_id", name="uq_teacher_assignment"),
    )


class Assessment(Base, TimestampMixin, SoftDeleteMixin):
    """Une évaluation (devoir, composition, examen...) pour une matière/classe/période."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # devoir / interrogation / composition / examen / projet / oral / pratique
    max_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("20.0"), nullable=False)
    coefficient: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("1.0"), nullable=False)

    grades: Mapped[list["Grade"]] = relationship(back_populates="assessment")


GRADE_STATES = ("draft", "submitted", "checked", "validated", "locked", "published")


class Grade(Base, TimestampMixin):
    """
    Une note d'un élève à une évaluation.
    Cycle d'état: draft -> submitted -> checked -> validated -> locked -> published.
    Toute modification après verrouillage doit passer par une autorisation
    explicite (tracée dans audit_logs) plutôt que par une écriture directe.
    """

    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="grades")

    __table_args__ = (UniqueConstraint("assessment_id", "student_id", name="uq_grade_per_student_assessment"),)


class GradeAudit(Base, TimestampMixin):
    """Historique des changements d'état et de valeur d'une note (traçabilité fine)."""

    __tablename__ = "grade_state_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id"), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False)
    old_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    new_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)


class ReportCard(Base, TimestampMixin):
    """Bulletin généré pour un élève, une période et une année scolaire."""

    __tablename__ = "report_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    academic_period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)

    general_average: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    class_rank: Mapped[int | None] = mapped_column(nullable=True)
    class_size: Mapped[int | None] = mapped_column(nullable=True)
    appreciation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "academic_period_id", name="uq_report_card_per_student_period"),
    )


class HonorBoardRule(Base, TimestampMixin, SoftDeleteMixin):
    """Règle configurable d'un tableau d'honneur (ex: Excellence: moyenne >= 14)."""

    __tablename__ = "honor_board_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    criteria: Mapped[dict] = mapped_column(  # {"min_average": 14, "max_unjustified_absences": 2, ...}
        JSON, default=dict, nullable=False
    )


class HonorBoardEntry(Base, TimestampMixin):
    """Résultat calculé d'un tableau d'honneur pour un élève à une période donnée."""

    __tablename__ = "honor_board_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("honor_board_rules.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"), nullable=True)
    academic_period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    unjustified_absences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("rule_id", "student_id", "academic_period_id", name="uq_honor_board_rule_student_period"),
    )
