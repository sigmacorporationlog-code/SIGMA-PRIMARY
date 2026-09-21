from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, BigInteger, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin

class FleetInstallation(Base, TimestampMixin):
    """Inventaire d'une installation SIGMA et état du dernier heartbeat."""
    __tablename__ = "fleet_installations"
    __table_args__ = (UniqueConstraint("school_id", name="uq_fleet_installation_school"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    instance_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    installed_version: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="commercial")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    disk_free_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

class FleetRollout(Base, TimestampMixin):
    """Déploiement progressif d'une version avec arrêt automatique en cas d'échec."""
    __tablename__ = "fleet_rollouts"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="commercial")
    strategy: Mapped[str] = mapped_column(String(30), nullable=False, default="canary")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned", index=True)
    canary_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_failure_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
