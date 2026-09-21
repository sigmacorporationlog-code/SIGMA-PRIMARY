from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin

class PlatformIncident(Base, TimestampMixin):
    __tablename__ = 'platform_incidents'
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey('schools.id'), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(20), default='medium', nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default='open', nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class PlatformMetricSnapshot(Base, TimestampMixin):
    __tablename__ = 'platform_metric_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    period_key: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    schools_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_schools: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    students_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_incidents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
