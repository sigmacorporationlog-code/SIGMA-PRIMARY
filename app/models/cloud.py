from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Integer, String, Text, UniqueConstraint, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class SchoolSubscription(Base, TimestampMixin):
    """Licence commerciale et état d'abonnement d'un établissement."""

    __tablename__ = "school_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, unique=True, index=True)
    plan_code: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="trial", nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_users: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    license_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    suspended_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    school: Mapped["School"] = relationship()


class CloudPlan(Base, TimestampMixin):
    """Catalogue des offres commerciales SIGMA."""

    __tablename__ = "cloud_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_price_xaf: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    annual_price_xaf: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CloudUsageSnapshot(Base, TimestampMixin):
    """Photo périodique de consommation pour supervision et facturation future."""

    __tablename__ = "cloud_usage_snapshots"
    __table_args__ = (UniqueConstraint("school_id", "period_key", name="uq_cloud_usage_school_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    students_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    api_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sync_operations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class CloudEvent(Base):
    """Événement de contrôle du plan Cloud (activation, changement, suspension)."""

    __tablename__ = "cloud_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
