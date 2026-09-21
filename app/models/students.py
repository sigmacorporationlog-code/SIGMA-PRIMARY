from datetime import date

from sqlalchemy import String, ForeignKey, Date, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Level(Base, TimestampMixin, SoftDeleteMixin):
    """Niveau scolaire (ex: 3e, 2nde)."""

    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(default=1, nullable=False)


class Stream(Base, TimestampMixin, SoftDeleteMixin):
    """Série / filière (ex: Scientifique, Littéraire)."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class SchoolClass(Base, TimestampMixin, SoftDeleteMixin):
    """Classe (ex: 3e A)."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"), nullable=False)
    stream_id: Mapped[int | None] = mapped_column(ForeignKey("streams.id"), nullable=True)
    campus_id: Mapped[int | None] = mapped_column(ForeignKey("campuses.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "3e A"
    homeroom_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    capacity: Mapped[int | None] = mapped_column(nullable=True)

    memberships: Mapped[list["ClassMembership"]] = relationship(back_populates="school_class")


class Guardian(Base, TimestampMixin, SoftDeleteMixin):
    """Père / mère / tuteur / personne autorisée à récupérer l'enfant."""

    __tablename__ = "guardians"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)  # père/mère/tuteur/autorisé
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    can_pick_up_child: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # accès portail parent


class Student(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)

    matricule: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)  # M/F
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    # active / transferred / dropped_out / excluded / graduated / conditional

    guardian_links: Mapped[list["StudentGuardian"]] = relationship(back_populates="student")
    memberships: Mapped[list["ClassMembership"]] = relationship(back_populates="student")

    __table_args__ = (UniqueConstraint("school_id", "matricule", name="uq_student_matricule_per_school"),)


class StudentGuardian(Base, TimestampMixin):
    __tablename__ = "student_guardians"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    guardian_id: Mapped[int] = mapped_column(ForeignKey("guardians.id"), nullable=False)
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student"] = relationship(back_populates="guardian_links")
    guardian: Mapped["Guardian"] = relationship()


class ClassMembership(Base, TimestampMixin):
    """
    Affectation d'un élève à une classe pour une année scolaire donnée.
    Ne jamais écraser: un élève peut redoubler, chaque année garde sa ligne.
    """

    __tablename__ = "class_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False)
    enrolled_at: Mapped[date] = mapped_column(Date, nullable=False)
    left_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrollment_type: Mapped[str] = mapped_column(String(30), default="inscription", nullable=False)
    # inscription / reinscription / transfert / mutation

    student: Mapped["Student"] = relationship(back_populates="memberships")
    school_class: Mapped["SchoolClass"] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("student_id", "class_id", "academic_year_id", name="uq_membership_year"),
    )
