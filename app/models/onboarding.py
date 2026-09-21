from sqlalchemy import String, ForeignKey, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin

class SchoolOnboarding(Base, TimestampMixin):
    __tablename__ = 'school_onboardings'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey('schools.id'), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), default='draft', nullable=False)
    current_step: Mapped[str] = mapped_column(String(50), default='school', nullable=False)
    completed_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    checklist: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (UniqueConstraint('school_id', name='uq_school_onboarding_school'),)
