from decimal import Decimal
from sqlalchemy import String, ForeignKey, Boolean, Text, Integer, UniqueConstraint, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class EvaluationFramework(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "evaluation_frameworks"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False)  # fr/en
    cycle: Mapped[str] = mapped_column(String(30), nullable=False)    # nursery/primary
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(30), default="2018", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gpa_mode: Mapped[str] = mapped_column(String(30), default="overall_scale", nullable=False)

    domains = relationship("EvaluationDomain", back_populates="framework", cascade="all, delete-orphan")
    scales = relationship("RatingScale", back_populates="framework", cascade="all, delete-orphan")
    appreciation_rules = relationship("AppreciationRule", back_populates="framework", cascade="all, delete-orphan")


class EvaluationDomain(Base, TimestampMixin):
    __tablename__ = "evaluation_domains"
    id: Mapped[int] = mapped_column(primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("evaluation_frameworks.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    framework = relationship("EvaluationFramework", back_populates="domains")
    competencies = relationship("EvaluationCompetency", back_populates="domain", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("framework_id", "code", name="uq_eval_domain_code"),)


class EvaluationCompetency(Base, TimestampMixin):
    __tablename__ = "evaluation_competencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("evaluation_domains.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    domain = relationship("EvaluationDomain", back_populates="competencies")
    criteria = relationship("EvaluationCriterion", back_populates="competency", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("domain_id", "code", name="uq_eval_comp_code"),)


class EvaluationCriterion(Base, TimestampMixin):
    __tablename__ = "evaluation_criteria"
    id: Mapped[int] = mapped_column(primary_key=True)
    competency_id: Mapped[int] = mapped_column(ForeignKey("evaluation_competencies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_mode: Mapped[str] = mapped_column(String(30), default="observation", nullable=False)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    competency = relationship("EvaluationCompetency", back_populates="criteria")
    __table_args__ = (UniqueConstraint("competency_id", "code", name="uq_eval_criterion_code"),)


class RatingScale(Base, TimestampMixin):
    __tablename__ = "rating_scales"
    id: Mapped[int] = mapped_column(primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("evaluation_frameworks.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    min_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    grade_point: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    framework = relationship("EvaluationFramework", back_populates="scales")
    __table_args__ = (UniqueConstraint("framework_id", "code", name="uq_rating_scale_code"),)


class EvaluationActivity(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "evaluation_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"), nullable=True)
    criterion_id: Mapped[int | None] = mapped_column(ForeignKey("evaluation_criteria.id"), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(30), default="formative", nullable=False)
    mode: Mapped[str] = mapped_column(String(30), default="observation", nullable=False)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    coefficient: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("1.0"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    results = relationship("EvaluationResult", back_populates="activity", cascade="all, delete-orphan")


class AppreciationRule(Base, TimestampMixin):
    __tablename__ = "evaluation_appreciation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("evaluation_frameworks.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    min_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    text_fr: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    framework = relationship("EvaluationFramework", back_populates="appreciation_rules")
    __table_args__ = (UniqueConstraint("framework_id", "code", name="uq_eval_appreciation_rule_code"),)


class EvaluationResult(Base, TimestampMixin):
    __tablename__ = "evaluation_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("evaluation_activities.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    rating_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_support: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    validated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    activity = relationship("EvaluationActivity", back_populates="results")
    __table_args__ = (UniqueConstraint("activity_id", "student_id", name="uq_eval_result_student_activity"),)


class EvaluationPeriodClosure(Base, TimestampMixin):
    """Clôture opérationnelle d'une classe et d'une période pédagogique."""
    __tablename__ = "evaluation_period_closures"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    academic_period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="closed", nullable=False)
    closed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    __table_args__ = (UniqueConstraint("class_id", "academic_period_id", name="uq_eval_period_closure"),)
