"""User management use cases within an organization.

Only admins create users, always within their own organization, respecting the plan's
active-user limit and email uniqueness.
"""

import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.evidence.application.audit_service import emit_audit_event
from app.identity.domain.constants import MembershipStatus, Role, UserStatus
from app.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    OperationNotAllowedError,
    UserLimitReachedError,
    UserNotFoundError,
)
from app.identity.domain.password import validate_password_strength
from app.identity.infrastructure.models import Membership, User
from app.identity.infrastructure.repositories import (
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)
from app.identity.infrastructure.token_store import TokenStore


async def create_user(
    session: AsyncSession,
    *,
    admin: User,
    full_name: str,
    email: str,
    password: str,
    role: Role,
    phone: str | None = None,
) -> User:
    """Creates a user in the authenticated admin's organization.

    The target organization always comes from the authenticated admin, never the payload.
    """
    email = email.strip().lower()
    validate_password_strength(password)

    organization = await OrganizationRepository(session).get_by_id(admin.organization_id)
    users = UserRepository(session)

    if organization.user_limit is not None:
        active = await users.count_active_by_organization(organization.id)
        if active >= organization.user_limit:
            raise UserLimitReachedError(organization.plan, organization.user_limit)

    if await users.get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError()

    user = User(
        organization_id=admin.organization_id,
        full_name=full_name,
        email=email,
        password_hash=security.hash_password(password),
        role=role.value,
        phone=phone,
    )
    users.add(user)
    await session.flush()  # populate user.id for the Membership row below

    MembershipRepository(session).add(
        Membership(
            user_id=user.id,
            organization_id=admin.organization_id,
            role=role.value,
            status=MembershipStatus.ACTIVE.value,
        )
    )

    await session.commit()
    await session.refresh(user)
    return user


async def list_users(session: AsyncSession, *, admin: User) -> list[User]:
    return await UserRepository(session).list_by_organization(admin.organization_id)


async def get_user(session: AsyncSession, *, admin: User, user_id: uuid.UUID) -> User:
    """404 also for users from other organizations (avoids leaking existence)."""
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or user.organization_id != admin.organization_id:
        raise UserNotFoundError()
    return user


async def update_user(
    session: AsyncSession,
    *,
    admin: User,
    user_id: uuid.UUID,
    fields: dict,
) -> User:
    user = await get_user(session, admin=admin, user_id=user_id)

    if user.id == admin.id and ("role" in fields or "status" in fields):
        raise OperationNotAllowedError("An admin cannot change their own role or status")

    # Reactivation counts against the plan limit again
    if fields.get("status") == UserStatus.ACTIVE.value and not user.is_active:
        organization = await OrganizationRepository(session).get_by_id(admin.organization_id)
        if organization.user_limit is not None:
            active = await UserRepository(session).count_active_by_organization(organization.id)
            if active >= organization.user_limit:
                raise UserLimitReachedError(organization.plan, organization.user_limit)

    for field, value in fields.items():
        setattr(user, field, value.value if hasattr(value, "value") else value)

    if "role" in fields or "status" in fields:
        membership = await MembershipRepository(session).get_by_user_and_organization(
            user.id, admin.organization_id
        )
        if membership is not None:
            if "role" in fields:
                membership.role = user.role
            if "status" in fields:
                # Mirrors deactivate_user's status mapping: only "active" keeps the
                # Membership active, every other User status revokes it.
                membership.status = (
                    MembershipStatus.ACTIVE.value
                    if user.status == UserStatus.ACTIVE.value
                    else MembershipStatus.REVOKED.value
                )

    await session.commit()
    await session.refresh(user)
    return user


async def deactivate_user(
    session: AsyncSession,
    redis: aioredis.Redis,
    *,
    admin: User,
    user_id: uuid.UUID,
) -> None:
    """Logical deactivation (no physical deletion) + revocation of active sessions."""
    user = await get_user(session, admin=admin, user_id=user_id)
    if user.id == admin.id:
        raise OperationNotAllowedError("An admin cannot deactivate their own account")

    user.status = UserStatus.INACTIVE.value

    membership = await MembershipRepository(session).get_by_user_and_organization(
        user.id, admin.organization_id
    )
    if membership is not None:
        membership.status = MembershipStatus.REVOKED.value

    await emit_audit_event(
        session,
        event_type="membership.revoked",
        actor_id=admin.id,
        organization_id=admin.organization_id,
        payload={
            "membership_id": str(membership.id) if membership is not None else None,
            "organization_id": str(admin.organization_id),
            "user_id": str(user.id),
            "revoked_by": str(admin.id),
        },
    )

    await session.commit()
    await TokenStore(redis).revoke_all_refresh_for_user(str(user.id))
