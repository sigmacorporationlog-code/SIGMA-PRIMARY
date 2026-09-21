from sqlalchemy import String, ForeignKey, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Regroupement de plusieurs établissements (groupe scolaire / réseau)."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    schools: Mapped[list["School"]] = relationship(back_populates="organization")


class School(Base, TimestampMixin, SoftDeleteMixin):
    """Un établissement scolaire (espace de données isolé)."""

    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(50), nullable=True)
    official_stamp_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ministry_name: Mapped[str] = mapped_column(String(255), default="Ministère de l’Éducation de Base", nullable=False)

    school_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # général/technique/pro
    regime: Mapped[str | None] = mapped_column(String(100), nullable=True)  # externat/internat...
    language: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="XAF", nullable=False)
    grading_system: Mapped[str] = mapped_column(String(50), default="20", nullable=False)
    matricule_strategy: Mapped[str] = mapped_column(String(40), default="year_sequence", nullable=False)
    matricule_template: Mapped[str] = mapped_column(String(80), default="{YY}{SEQ:05}", nullable=False)
    matricule_next_sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    badge_next_sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    # Canal utilisé par défaut pour les envois aux parents : "sms" (boîtier
    # GSM/passerelle SMS), "app" (notification push app mobile SIGMA) ou
    # "both". Un envoi peut toujours forcer un canal différent au cas par
    # cas ; ceci ne fixe que le comportement par défaut de l'établissement.
    communication_channel_default: Mapped[str] = mapped_column(String(20), default="sms", nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="schools")
    campuses: Mapped[list["Campus"]] = relationship(back_populates="school")
    academic_years: Mapped[list["AcademicYear"]] = relationship(back_populates="school")


class Campus(Base, TimestampMixin, SoftDeleteMixin):
    """Site physique d'un établissement (mode multisite)."""

    __tablename__ = "campuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    school: Mapped["School"] = relationship(back_populates="campuses")


class AcademicYear(Base, TimestampMixin):
    """Année scolaire. Une année clôturée devient archivée et protégée."""

    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)  # ex: "2026/2027"
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    school: Mapped["School"] = relationship(back_populates="academic_years")


class AcademicPeriod(Base, TimestampMixin):
    """Période/trimestre/semestre d'une année scolaire."""

    __tablename__ = "academic_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Trimestre 1"
    order_index: Mapped[int] = mapped_column(default=1, nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    is_grade_entry_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
