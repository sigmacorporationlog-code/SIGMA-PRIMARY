from datetime import date, datetime

from sqlalchemy import String, ForeignKey, Date, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class CardTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """
    Modèle éditable de carte (scolaire / d'accès / de bibliothèque, etc.).
    `layout` est un JSON libre décrivant les champs affichés, les couleurs,
    le logo et la mise en page — modifiable sans intervention du développeur
    (cahier des charges §46).
    """

    __tablename__ = "card_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    card_type: Mapped[str] = mapped_column(String(30), default="student_id", nullable=False)
    # student_id / staff_id / library / access

    layout: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # ex: {"primary_color": "#11633A", "accent_color": "#FF8A00",
    #      "fields": ["matricule", "full_name", "class", "birth_date"],
    #      "show_qr": true, "show_photo": true}

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class IdCard(Base, TimestampMixin):
    """
    Une carte émise pour un élève ou un membre du personnel. Sert de badge
    d'accès (portail/QR) et de pièce d'identité scolaire.
    """

    __tablename__ = "id_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("card_templates.id"), nullable=False)

    holder_type: Mapped[str] = mapped_column(String(20), nullable=False)  # student / staff
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    card_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # ex: CARD-2026-000452
    access_code: Mapped[str] = mapped_column(String(100), nullable=False)  # payload encodé dans le QR
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # active / printed / delivered / lost / damaged / revoked / replaced
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    print_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifecycle_note: Mapped[str | None] = mapped_column(Text, nullable=True)
