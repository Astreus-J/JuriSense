"""User invitations.

An admin invites by email; the invitee sets their own password on acceptance. Resending
an invitation cancels the previous one; acceptance respects the plan's user limit and
email uniqueness.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.identity.domain.constants import InvitationStatus, MembershipStatus, Role
from app.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidInvitationError,
    UserLimitReachedError,
)
from app.identity.domain.password import validate_password_strength
from app.identity.domain.ports import EmailSender
from app.identity.domain.rules import is_expired
from app.identity.infrastructure.models import Invitation, Membership, User
from app.identity.infrastructure.repositories import (
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)


async def _check_user_limit(session: AsyncSession, organization_id) -> None:
    organization = await OrganizationRepository(session).get_by_id(organization_id)
    if organization.user_limit is None:
        return
    active = await UserRepository(session).count_active_by_organization(organization.id)
    if active >= organization.user_limit:
        raise UserLimitReachedError(organization.plan, organization.user_limit)


async def invite_user(
    session: AsyncSession,
    email_sender: EmailSender,
    *,
    admin: User,
    email: str,
    role: Role,
    full_name: str | None = None,
) -> Invitation:
    settings = get_settings()
    email = email.strip().lower()

    if await UserRepository(session).get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError()
    await _check_user_limit(session, admin.organization_id)

    invitations = InvitationRepository(session)
    await invitations.cancel_pending(email, admin.organization_id)

    token, token_hash = security.generate_opaque_token()
    invitation = Invitation(
        email=email,
        full_name=full_name,
        role=role.value,
        token_hash=token_hash,
        organization_id=admin.organization_id,
        invited_by_id=admin.id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.invite_expire_days),
    )
    invitations.add(invitation)
    await session.flush()  # populate invitation.id for the audit payload below

    await emit_audit_event(
        session,
        event_type="membership.invited",
        actor_id=admin.id,
        organization_id=admin.organization_id,
        payload={
            # No Membership row exists yet for an invitee who isn't a User yet (a
            # Membership requires a user_id); the pending Invitation is the durable
            # record of this action until acceptance creates the real Membership.
            "invitation_id": str(invitation.id),
            "organization_id": str(admin.organization_id),
            "invited_email": email,
            "role": role.value,
            "invited_by": str(admin.id),
        },
    )
    await session.commit()
    await session.refresh(invitation)

    link = f"{settings.frontend_url}/accept-invite?token={token}"
    await email_sender.send(
        to=email,
        subject="JuriSense — You've been invited",
        body=(
            f"{admin.full_name} invited you to join the team on JuriSense.\n\n"
            f"To create your account, visit: {link}\n\n"
            f"This invitation expires in {settings.invite_expire_days} days."
        ),
    )
    return invitation


async def accept_invitation(
    session: AsyncSession,
    *,
    token: str,
    password: str,
    full_name: str | None = None,
) -> User:
    invitations = InvitationRepository(session)
    invitation = await invitations.get_pending_by_hash(security.hash_opaque_token(token))
    if invitation is None:
        raise InvalidInvitationError()
    if is_expired(invitation.expires_at):
        invitation.status = InvitationStatus.EXPIRED.value
        await session.commit()
        raise InvalidInvitationError()

    validate_password_strength(password)

    users = UserRepository(session)
    if await users.get_by_email(invitation.email) is not None:
        raise EmailAlreadyRegisteredError()
    await _check_user_limit(session, invitation.organization_id)

    name = full_name or invitation.full_name
    if not name:
        raise InvalidInvitationError()

    user = User(
        organization_id=invitation.organization_id,
        full_name=name,
        email=invitation.email,
        password_hash=security.hash_password(password),
        role=invitation.role,
    )
    users.add(user)
    await session.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=invitation.organization_id,
        role=invitation.role,
        status=MembershipStatus.ACTIVE.value,
    )
    MembershipRepository(session).add(membership)
    await session.flush()

    invitation.status = InvitationStatus.ACCEPTED.value
    invitation.accepted_by_id = user.id
    invitation.accepted_at = datetime.now(UTC)

    await emit_audit_event(
        session,
        event_type="membership.accepted",
        actor_id=user.id,
        organization_id=invitation.organization_id,
        payload={
            "membership_id": str(membership.id),
            "organization_id": str(invitation.organization_id),
            "user_id": str(user.id),
            "role": invitation.role,
            "accepted_at": invitation.accepted_at.isoformat(),
        },
    )

    await session.commit()
    await session.refresh(user)
    return user


async def list_invitations(session: AsyncSession, *, admin: User) -> list[Invitation]:
    return await InvitationRepository(session).list_by_organization(admin.organization_id)
