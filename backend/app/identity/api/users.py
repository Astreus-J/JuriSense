import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.db import SessionDep
from app.core.redis import RedisDep
from app.identity.api.deps import CurrentAdmin, EmailDep
from app.identity.api.schemas import (
    AcceptInviteRequest,
    CreateUserRequest,
    InvitationResponse,
    InviteRequest,
    UpdateUserRequest,
    UserResponse,
)
from app.identity.application import invite_service, user_service
from app.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidInvitationError,
    OperationNotAllowedError,
    UserLimitReachedError,
    UserNotFoundError,
    WeakPasswordError,
)

router = APIRouter(prefix="/users", tags=["users"])


def _map_error(exc: Exception) -> HTTPException:
    """Translates domain errors into HTTP responses."""
    match exc:
        case WeakPasswordError():
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{exc.message}: {', '.join(exc.reasons)}",
            )
        case UserLimitReachedError():
            return HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=exc.message)
        case EmailAlreadyRegisteredError():
            return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
        case UserNotFoundError():
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
        case OperationNotAllowedError():
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
        case InvalidInvitationError():
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
        case _:  # pragma: no cover — a programming error, not an input error
            raise exc


# ---- Invitations (before the {user_id} routes so they don't collide) ----


@router.post("/invites", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteRequest, admin: CurrentAdmin, session: SessionDep, email_sender: EmailDep
) -> InvitationResponse:
    """Invites a user into the admin's organization; resending cancels the previous one."""
    try:
        invitation = await invite_service.invite_user(
            session,
            email_sender,
            admin=admin,
            email=body.email,
            role=body.role,
            full_name=body.full_name,
        )
    except Exception as exc:  # noqa: BLE001 — translated by _map_error
        raise _map_error(exc) from exc
    return InvitationResponse.model_validate(invitation)


@router.get("/invites", response_model=list[InvitationResponse])
async def list_invites(admin: CurrentAdmin, session: SessionDep) -> list[InvitationResponse]:
    invitations = await invite_service.list_invitations(session, admin=admin)
    return [InvitationResponse.model_validate(i) for i in invitations]


@router.post(
    "/accept-invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def accept_invite(body: AcceptInviteRequest, session: SessionDep) -> UserResponse:
    """Public endpoint: the invitee sets their password and joins the invitation's organization."""
    try:
        user = await invite_service.accept_invitation(
            session, token=body.token, password=body.password, full_name=body.full_name
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UserResponse.model_validate(user)


# ---- User CRUD ----


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest, admin: CurrentAdmin, session: SessionDep
) -> UserResponse:
    """Creates a user in the authenticated admin's organization."""
    try:
        user = await user_service.create_user(
            session,
            admin=admin,
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            role=body.role,
            phone=body.phone,
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
async def list_users(admin: CurrentAdmin, session: SessionDep) -> list[UserResponse]:
    users = await user_service.list_users(session, admin=admin)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, admin: CurrentAdmin, session: SessionDep) -> UserResponse:
    try:
        user = await user_service.get_user(session, admin=admin, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID, body: UpdateUserRequest, admin: CurrentAdmin, session: SessionDep
) -> UserResponse:
    try:
        user = await user_service.update_user(
            session,
            admin=admin,
            user_id=user_id,
            fields=body.model_dump(exclude_unset=True),
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID, admin: CurrentAdmin, session: SessionDep, redis: RedisDep
) -> None:
    """Logical deactivation (no physical deletion)."""
    try:
        await user_service.deactivate_user(session, redis, admin=admin, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
