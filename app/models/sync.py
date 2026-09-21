from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, JSON, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin, utcnow


class SyncDevice(Base, TimestampMixin):
    """Poste client identifié de façon stable pour le réseau/local offline."""
    __tablename__ = "sync_devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="client", nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="online", nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("school_id", "device_id", name="uq_sync_device_school_device"),)


class SyncOperation(Base, TimestampMixin):
    """Journal idempotent des opérations produites par un client offline/online.

    v1.7 ne prétend pas appliquer automatiquement des mutations arbitraires :
    il sécurise d'abord la file, l'idempotence et la détection de conflit.
    """
    __tablename__ = "sync_operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    base_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    server_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    superseded_by_operation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class SyncEntityVersion(Base):
    """Version logique par entité utilisée pour préparer la résolution de conflits."""
    __tablename__ = "sync_entity_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("school_id", "entity_type", "entity_id", name="uq_sync_entity_version"),)


class SyncEntityIdentity(Base):
    """Correspondance entre un identifiant client stable et l'identifiant serveur."""
    __tablename__ = "sync_entity_identities"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    client_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    server_entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (
        UniqueConstraint("school_id", "entity_type", "client_entity_id", name="uq_sync_identity_client"),
        UniqueConstraint("school_id", "entity_type", "server_entity_id", name="uq_sync_identity_server"),
    )


class SyncDeliveryAck(Base):
    """Accusé de réception par poste pour éviter les rediffusions inutiles."""
    __tablename__ = "sync_delivery_acks"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("school_id", "device_id", "operation_id", name="uq_sync_delivery_ack"),)
