"""Destinations cloud pour la sauvegarde (Google Drive, OneDrive, Dropbox...).

Une école peut connecter plusieurs comptes cloud à la fois (ex: Google Drive
en principal, Dropbox en secours) ; chaque sauvegarde locale réussie est
ensuite poussée vers toutes les destinations actives.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

SUPPORTED_PROVIDERS = ("google_drive", "onedrive", "dropbox")


class CloudBackupDestination(Base, TimestampMixin):
    __tablename__ = "cloud_backup_destinations"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # Jetons chiffrés au repos (voir app/services/crypto.py) — jamais
    # renvoyés en clair par l'API, y compris pour un admin superadmin.
    encrypted_access_token: Mapped[str] = mapped_column(String(2000), nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    folder_path: Mapped[str] = mapped_column(String(300), default="/SIGMA", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    school = relationship("School")
