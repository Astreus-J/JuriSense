"""Authentication use cases: registration, login, refresh, and logout."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application.workflow_service import seed_default_workflows
from app.core import security
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.identity.application.permission_service import seed_default_permissions
from app.identity.domain.constants import PLAN_LIMITS, MembershipStatus, Plan, Role
from app.identity.domain.errors import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserInactiveError,
)
from app.identity.domain.password import validate_password_strength
from app.identity.infrastructure.lockout import LoginLockout
from app.identity.infrastructure.models import AccessLog, Membership, Organization, User
from app.identity.infrastructure.repositories import (
    AccessLogRepository,
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)
from app.identity.infrastructure.token_store import TokenStore


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _build_lockout(redis: aioredis.Redis) -> LoginLockout:
    settings = get_settings()
    return LoginLockout(
        redis,
        max_attempts=settings.login_max_attempts,
        lockout_seconds=settings.login_lockout_minutes * 60,
    )


async def _issue_tokens(redis: aioredis.Redis, user_id: uuid.UUID) -> TokenPair:
    settings = get_settings()
    access_token, _ = security.create_access_token(user_id)
    refresh_token, refresh_jti = security.create_refresh_token(user_id)
    await TokenStore(redis).store_refresh(
        refresh_jti,
        str(user_id),
        ttl_seconds=settings.refresh_token_expire_days * 24 * 3600,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def register_organization(
    session: AsyncSession,
    *,
    organization_name: str,
    full_name: str,
    email: str,
    password: str,
    phone: str | None = None,
    plan: Plan = Plan.STARTER,
) -> User:
    """Creates the organization (with the chosen plan's limits) and its admin user."""
    email = _normalize_email(email)
    validate_password_strength(password)

    users = UserRepository(session)
    if await users.get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError()

    limits = PLAN_LIMITS[plan]
    organization = Organization(
        name=organization_name,
        plan=plan.value,
        user_limit=limits.user_limit,
        supplier_limit=limits.supplier_limit,
        storage_limit_gb=limits.storage_limit_gb,
        ai_execution_limit=limits.ai_execution_limit,
    )
    OrganizationRepository(session).add(organization)

    admin = User(
        organization=organization,
        full_name=full_name,
        email=email,
        password_hash=security.hash_password(password),
        phone=phone,
        role=Role.ADMIN.value,
    )
    users.add(admin)
    await session.flush()  # populate organization.id/admin.id for the audit payload below

    MembershipRepository(session).add(
        Membership(
            user_id=admin.id,
            organization_id=organization.id,
            role=Role.ADMIN.value,
            status=MembershipStatus.ACTIVE.value,
        )
    )
    await seed_default_permissions(session, user=admin, role=Role.ADMIN)
    # FEATURE-6.1: bootstraps this brand-new organization's default ApprovalWorkflow rows
    # (medium/high/critical), the same "seed a sane default at registration time" shape as
    # seed_default_permissions above. Identity & Organizations calling into Approvals &
    # Decisions here is a deliberate exception to the usual dependency direction (other
    # contexts call into Approvals & Decisions, not the reverse) -- organization
    # registration is the one place a new organization's defaults are provisioned in one
    # transaction, and without this call every organization would need an explicit admin
    # setup step before its first REVIEW-outcome compliance review could be routed
    # anywhere at all. See `app.approvals.application.workflow_service.seed_default_workflows`'s
    # own docstring for the full rationale.
    await seed_default_workflows(session, organization_id=organization.id)
    await emit_audit_event(
        session,
        event_type="organization.created",
        actor_id=admin.id,
        organization_id=organization.id,
        payload={
            "organization_id": str(organization.id),
            "name": organization.name,
            "tax_id": organization.tax_id,
            "plan": organization.plan,
            "created_by": str(admin.id),
        },
    )
    await emit_audit_event(
        session,
        event_type="user.registered",
        actor_id=admin.id,
        organization_id=organization.id,
        payload={"user_id": str(admin.id), "email": admin.email},
    )

    await session.commit()
    await session.refresh(admin)
    return admin


async def login(
    session: AsyncSession,
    redis: aioredis.Redis,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> TokenPair:
    email = _normalize_email(email)
    lockout = _build_lockout(redis)

    retry_after = await lockout.seconds_until_unlock(email)
    if retry_after is not None:
        raise AccountLockedError(retry_after)

    user = await UserRepository(session).get_by_email(email)

    async def _fail() -> None:
        await lockout.register_failure(email)
        AccessLogRepository(session).add(
            AccessLog(
                user_id=user.id if user else None,
                email=email,
                ip=ip,
                user_agent=user_agent,
                successful=False,
            )
        )
        await session.commit()

    if user is None:
        security.verify_dummy_password(password)
        await _fail()
        raise InvalidCredentialsError()

    if not security.verify_password(password, user.password_hash):
        await _fail()
        raise InvalidCredentialsError()

    if not user.is_active:
        raise UserInactiveError()

    await lockout.reset(email)
    user.last_login_at = datetime.now(UTC)
    AccessLogRepository(session).add(
        AccessLog(user_id=user.id, email=email, ip=ip, user_agent=user_agent, successful=True)
    )
    await session.commit()
    return await _issue_tokens(redis, user.id)


async def refresh_tokens(
    session: AsyncSession, redis: aioredis.Redis, *, refresh_token: str
) -> TokenPair:
    """Refresh rotation: the used token is invalidated and a new pair is issued."""
    try:
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN)
    except security.TokenError as exc:
        raise InvalidRefreshTokenError() from exc

    user_id = await TokenStore(redis).consume_refresh(payload["jti"])
    if user_id is None or user_id != payload["sub"]:
        raise InvalidRefreshTokenError()

    user = await UserRepository(session).get_by_id(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    return await _issue_tokens(redis, user.id)


async def logout(redis: aioredis.Redis, *, access_payload: dict, refresh_token: str | None) -> None:
    """Revokes the refresh token and blocks the access token until it expires."""
    store = TokenStore(redis)

    exp = datetime.fromtimestamp(access_payload["exp"], tz=UTC)
    remaining = int((exp - datetime.now(UTC)).total_seconds())
    await store.block_access(access_payload["jti"], remaining)

    if refresh_token is None:
        return
    try:
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN)
    except security.TokenError:
        return  # refresh already invalid; nothing to revoke
    if payload["sub"] == access_payload["sub"]:
        await store.revoke_refresh(payload["jti"])
