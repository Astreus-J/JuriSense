"""Password recovery.

Single-use token with a 1h expiry; the response never reveals whether the email exists;
after the change, all of the user's sessions are revoked (MED-001) and they are notified
by email.
"""

from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.identity.domain.errors import InvalidPasswordResetTokenError
from app.identity.domain.password import validate_password_strength
from app.identity.domain.ports import EmailSender
from app.identity.domain.rules import is_expired
from app.identity.infrastructure.models import PasswordResetToken
from app.identity.infrastructure.repositories import (
    PasswordResetTokenRepository,
    UserRepository,
)
from app.identity.infrastructure.token_store import TokenStore


async def request_password_reset(
    session: AsyncSession, email_sender: EmailSender, *, email: str
) -> None:
    """Always silent: the caller responds generically whether or not the email exists."""
    settings = get_settings()
    email = email.strip().lower()

    user = await UserRepository(session).get_by_email(email)
    if user is None or not user.is_active:
        return

    tokens = PasswordResetTokenRepository(session)
    await tokens.invalidate_all_for_user(user.id)

    token, token_hash = security.generate_opaque_token()
    tokens.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.password_reset_expire_minutes),
        )
    )
    await session.commit()

    link = f"{settings.frontend_url}/reset-password?token={token}"
    await email_sender.send(
        to=email,
        subject="JuriSense — Password recovery",
        body=(
            f"Hello, {user.full_name}.\n\n"
            f"To reset your password, visit: {link}\n\n"
            f"This link expires in {settings.password_reset_expire_minutes} minutes. "
            "If you did not request this, ignore this email."
        ),
    )


async def reset_password(
    session: AsyncSession,
    redis: aioredis.Redis,
    email_sender: EmailSender,
    *,
    token: str,
    new_password: str,
) -> None:
    validate_password_strength(new_password)

    record = await PasswordResetTokenRepository(session).get_valid_by_hash(
        security.hash_opaque_token(token)
    )
    if record is None or is_expired(record.expires_at):
        raise InvalidPasswordResetTokenError()

    user = await UserRepository(session).get_by_id(record.user_id)
    if user is None or not user.is_active:
        raise InvalidPasswordResetTokenError()

    user.password_hash = security.hash_password(new_password)
    record.used = True
    await emit_audit_event(
        session,
        event_type="user.password_reset",
        actor_id=user.id,
        organization_id=user.organization_id,
        payload={
            "user_id": str(user.id),
            "initiated_via": "self_service",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    await session.commit()

    # Old sessions stop being valid (MED-001)
    await TokenStore(redis).revoke_all_refresh_for_user(str(user.id))

    await email_sender.send(
        to=user.email,
        subject="JuriSense — Your password was changed",
        body=(
            f"Hello, {user.full_name}.\n\n"
            "Your account password was changed and all active sessions were terminated. "
            "If this wasn't you, contact support immediately."
        ),
    )
