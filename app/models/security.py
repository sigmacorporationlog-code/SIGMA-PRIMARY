"""
Le coeur de SIGMA: moteur d'habilitation.

Règle d'or du projet: les fonctionnalités sont séparées de l'autorisation d'y
accéder. Un utilisateur détient un ou plusieurs POSTES. Chaque poste porte des
PERMISSIONS, elles-mêmes potentiellement restreintes à un PÉRIMÈTRE (scope) :
établissement, campus, niveau, série, classe, matière, période, ou "ses
propres dossiers".
"""
from datetime import datetime, date

from sqlalchemy import String, ForeignKey, Boolean, DateTime, Date, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_version: Mapped[int] = mapped_column(default=1, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user_posts: Mapped[list["UserPost"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Post(Base, TimestampMixin, SoftDeleteMixin):
    """
    Un "poste" (ex: Responsable de la vie scolaire, Enseignant, Comptable).
    Créé et défini librement par l'administrateur de chaque établissement.
    """

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    permissions: Mapped[list["PostPermission"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    user_posts: Mapped[list["UserPost"]] = relationship(back_populates="post")


class Permission(Base, TimestampMixin):
    """
    Catalogue fixe des permissions atomiques que le code sait appliquer.
    Exemple de code: "academic.grades.create", "finance.payments.cancel".
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False)  # students/academic/finance/administration...
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class PostPermission(Base, TimestampMixin):
    """
    Association Poste <-> Permission, avec un périmètre (scope) optionnel en JSON.
    scope = {"level_id": .., "stream_id": .., "class_id": .., "subject_id": ..,
             "campus_id": .., "period_id": .., "own_records_only": true}
    Un scope vide ({}) signifie "tout l'établissement".
    """

    __tablename__ = "post_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    post: Mapped["Post"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship()

    __table_args__ = (UniqueConstraint("post_id", "permission_id", "scope", name="uq_post_permission_scope"),)


class UserPost(Base, TimestampMixin):
    """Un utilisateur peut occuper plusieurs postes simultanément."""

    __tablename__ = "user_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="user_posts")
    post: Mapped["Post"] = relationship(back_populates="user_posts")

    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_user_post"),)


class Delegation(Base, TimestampMixin):
    """
    Délégation temporaire d'une autorisation d'un utilisateur à un autre,
    pour une période donnée. Expire automatiquement (voir service dédié).
    """

    __tablename__ = "delegations"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    granted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    granted_to_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PasswordResetToken(Base):
    """Jeton de récupération à usage unique, stocké uniquement sous forme de hash."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AuditLog(Base):
    """
    Journal d'audit non modifiable par les utilisateurs ordinaires.
    Toute opération sensible (créer/modifier/supprimer/annuler) y est tracée.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    action: Mapped[str] = mapped_column(String(100), nullable=False)  # ex: "payment.update"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
