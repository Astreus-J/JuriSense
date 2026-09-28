import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.constants import InvitationStatus, UserStatus
from app.identity.infrastructure.models import (
    AccessLog,
    Invitation,
    Membership,
    ModulePermission,
    Organization,
    PasswordResetToken,
    User,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def count_active_by_organization(self, organization_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(User.id)).where(
                User.organization_id == organization_id,
                User.status == UserStatus.ACTIVE.value,
            )
        )
        return result.scalar_one()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[User]:
        result = await self._session.execute(
            select(User).where(User.organization_id == organization_id).order_by(User.created_at)
        )
        return list(result.scalars())

    def add(self, user: User) -> None:
        self._session.add(user)


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used.is_(False),
            )
        )
        for token in result.scalars():
            token.used = True

    def add(self, token: PasswordResetToken) -> None:
        self._session.add(token)


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pending_by_hash(self, token_hash: str) -> Invitation | None:
        result = await self._session.execute(
            select(Invitation).where(
                Invitation.token_hash == token_hash,
                Invitation.status == InvitationStatus.PENDING.value,
            )
        )
        return result.scalar_one_or_none()

    async def cancel_pending(self, email: str, organization_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(Invitation).where(
                Invitation.email == email,
                Invitation.organization_id == organization_id,
                Invitation.status == InvitationStatus.PENDING.value,
            )
        )
        for invitation in result.scalars():
            invitation.status = InvitationStatus.CANCELLED.value

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Invitation]:
        result = await self._session.execute(
            select(Invitation)
            .where(Invitation.organization_id == organization_id)
            .order_by(Invitation.created_at.desc())
        )
        return list(result.scalars())

    def add(self, invitation: Invitation) -> None:
        self._session.add(invitation)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return await self._session.get(Organization, organization_id)

    def add(self, organization: Organization) -> None:
        self._session.add(organization)


class AccessLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, access_log: AccessLog) -> None:
        self._session.add(access_log)


class MembershipRepository:
    """See Membership (infrastructure/models.py) for why this table is additive to
    User.organization_id/role — it exists so a User can hold more than one Membership
    (BR-ORG-001), proven by tests/identity/test_membership.py.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_and_organization(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Membership | None:
        result = await self._session.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Membership]:
        result = await self._session.execute(
            select(Membership).where(Membership.user_id == user_id)
        )
        return list(result.scalars())

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Membership]:
        result = await self._session.execute(
            select(Membership).where(Membership.organization_id == organization_id)
        )
        return list(result.scalars())

    def add(self, membership: Membership) -> None:
        self._session.add(membership)


class ModulePermissionRepository:
    """Per-user x module x organization RBAC grid (ADR-003/ADR-012).

    A row is created for every (user, module) pair at user-creation time from that user's
    role default grid (`app.identity.domain.rbac.DEFAULT_ROLE_GRID`, wired in
    `permission_service.seed_default_permissions`); an admin may later edit a specific row
    to grant a per-user override beyond the role default (STORY-0.2.4).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_module(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, module: str
    ) -> ModulePermission | None:
        result = await self._session.execute(
            select(ModulePermission).where(
                ModulePermission.user_id == user_id,
                ModulePermission.organization_id == organization_id,
                ModulePermission.module == module,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ModulePermission]:
        result = await self._session.execute(
            select(ModulePermission).where(
                ModulePermission.user_id == user_id,
                ModulePermission.organization_id == organization_id,
            )
        )
        return list(result.scalars())

    def add(self, module_permission: ModulePermission) -> None:
        self._session.add(module_permission)
