import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security
from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.redis import RedisDep
from app.identity.domain.constants import Role
from app.identity.domain.ports import EmailSender
from app.identity.infrastructure.email import ConsoleEmailSender, SMTPEmailSender
from app.identity.infrastructure.models import User
from app.identity.infrastructure.repositories import UserRepository
from app.identity.infrastructure.token_store import TokenStore

_bearer = HTTPBearer(auto_error=False)

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    redis: RedisDep,
) -> dict[str, Any]:
    if credentials is None:
        raise _INVALID_CREDENTIALS
    try:
        payload = security.decode_token(credentials.credentials, security.ACCESS_TOKEN)
    except security.TokenError as exc:
        raise _INVALID_CREDENTIALS from exc
    if await TokenStore(redis).is_access_blocked(payload["jti"]):
        raise _INVALID_CREDENTIALS
    return payload


AccessPayload = Annotated[dict[str, Any], Depends(get_access_payload)]


async def get_current_user(payload: AccessPayload, session: SessionDep) -> User:
    user = await UserRepository(session).get_by_id(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise _INVALID_CREDENTIALS
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def get_email_sender() -> EmailSender:
    if get_settings().smtp_host:
        return SMTPEmailSender()
    return ConsoleEmailSender()


EmailDep = Annotated[EmailSender, Depends(get_email_sender)]
