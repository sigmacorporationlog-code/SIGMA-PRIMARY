from datetime import date

from sqlalchemy import String, ForeignKey, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # present/absent/late/excused_leave
    is_justified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    justification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class DisciplinaryRecord(Base, TimestampMixin):
    __tablename__ = "disciplinary_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    record_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # observation / warning / detention / sanction / exclusion / commendation
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low/medium/high
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reported_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
