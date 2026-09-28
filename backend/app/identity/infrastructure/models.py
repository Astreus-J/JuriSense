import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.identity.domain.constants import (
    InvitationStatus,
    MembershipStatus,
    Plan,
    Role,
    UserStatus,
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    # Jurisdiction-specific tax identifier (CNPJ for the Brazil pack; other jurisdiction
    # packs will use their own format — see docs/00-project/overview.md "Internationalization").
    tax_id: Mapped[str | None] = mapped_column(String(18), unique=True, index=True, default=None)

    contact_email: Mapped[str | None] = mapped_column(String(320), default=None)
    phone: Mapped[str | None] = mapped_column(String(28), default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    state: Mapped[str | None] = mapped_column(String(2), default=None)
    postal_code: Mapped[str | None] = mapped_column(String(9), default=None)

    # Commercial plan and its limits, derived at creation time (None = unlimited).
    # See PlanLimits/PLAN_LIMITS (domain/constants.py) for the dimension definitions.
    plan: Mapped[str] = mapped_column(String(20), default=Plan.STARTER.value)
    user_limit: Mapped[int | None] = mapped_column(default=1)
    supplier_limit: Mapped[int | None] = mapped_column(default=250)
    storage_limit_gb: Mapped[int | None] = mapped_column(default=15)
    ai_execution_limit: Mapped[int | None] = mapped_column(default=50)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="organization", foreign_keys="User.organization_id"
    )
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_organization_role", "organization_id", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), default=None)

    role: Mapped[str] = mapped_column(String(30), default=Role.ADMIN.value)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)

    # 2FA TOTP
    two_factor_enabled: Mapped[bool] = mapped_column(default=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String(32), default=None)

    email_verified: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(
        back_populates="users", foreign_keys=[organization_id]
    )

    @property
    def is_active(self) -> bool:
        """Derived from status: only users with status 'active' can authenticate."""
        return self.status == UserStatus.ACTIVE.value


class Membership(Base):
    """Links a User to an Organization with a Role (docs/03-domain/domain-model.md).

    Additive to the existing `User.organization_id`/`role` columns, which remain the
    "home" organization/role a user authenticates and is scoped by today. This table
    exists so a User CAN hold more than one Membership (BR-ORG-001) — e.g. a consultant
    belonging to two organizations — even though the org-switcher UI/API that lets a user
    act under a second membership is out of scope for this Epic (tracked as
    FEATURE-1.2/STORY-1.2.1). See STORY-0.2.5.
    """

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default=MembershipStatus.ACTIVE.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    organization: Mapped[Organization] = relationship(
        back_populates="memberships", foreign_keys=[organization_id]
    )


class ModulePermission(Base):
    """Granular per-user × module × action permission override (ADR-003/ADR-012)."""

    __tablename__ = "module_permissions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "module", "organization_id", name="uq_module_permission_user_module_org"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    module: Mapped[str] = mapped_column(String(50))

    can_create: Mapped[bool] = mapped_column(default=False)
    can_read: Mapped[bool] = mapped_column(default=False)
    can_update: Mapped[bool] = mapped_column(default=False)
    can_delete: Mapped[bool] = mapped_column(default=False)

    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    granted_by: Mapped[User | None] = relationship(foreign_keys=[granted_by_id])


class PasswordResetToken(Base):
    """Password reset token — stores only the SHA-256 hash.

    The opaque token itself only ever exists in the emailed link; a database leak alone
    cannot be used to reset a password.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    used: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class Invitation(Base):
    """Invitation of a user into an organization with a given role."""

    __tablename__ = "invitations"
    __table_args__ = (
        Index("ix_invitations_email_organization", "email", "organization_id"),
        Index("ix_invitations_status_expires_at", "status", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)
    role: Mapped[str] = mapped_column(String(30))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=InvitationStatus.PENDING.value)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    accepted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship()
    invited_by: Mapped[User | None] = relationship(foreign_keys=[invited_by_id])
    accepted_by: Mapped[User | None] = relationship(foreign_keys=[accepted_by_id])


class AccessLog(Base):
    """Login attempt history."""

    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True, default=None
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    ip: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    successful: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
