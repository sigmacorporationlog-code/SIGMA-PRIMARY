from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class SmsMessage(Base, TimestampMixin):
    """
    Un SMS envoyé (ou tenté) via le boîtier SMS de l'établissement.
    Conservé même en cas d'échec, pour traçabilité et pour permettre un
    nouvel essai (retry) manuel ou automatique.
    """

    __tablename__ = "sms_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    sent_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    recipient_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ex: "Mme Ebomo (mère)"
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    guardian_id: Mapped[int | None] = mapped_column(ForeignKey("guardians.id"), nullable=True)

    body: Mapped[str] = mapped_column(Text, nullable=False)
    campaign_label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ex: "Impayés - relance"

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending / sent / failed
    provider_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
