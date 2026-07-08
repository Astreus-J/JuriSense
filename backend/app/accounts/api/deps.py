import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.accounts.domain.constants import Perfil
from app.accounts.domain.ports import EmailSender
from app.accounts.infrastructure.email import ConsoleEmailSender, SMTPEmailSender
from app.accounts.infrastructure.models import Usuario
from app.accounts.infrastructure.repositories import UsuarioRepository
from app.accounts.infrastructure.token_store import TokenStore
from app.core import security
from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.redis import RedisDep

_bearer = HTTPBearer(auto_error=False)

_CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    redis: RedisDep,
) -> dict[str, Any]:
    if credentials is None:
        raise _CREDENCIAIS_INVALIDAS
    try:
        payload = security.decode_token(credentials.credentials, security.ACCESS_TOKEN)
    except security.TokenError as exc:
        raise _CREDENCIAIS_INVALIDAS from exc
    if await TokenStore(redis).is_access_blocked(payload["jti"]):
        raise _CREDENCIAIS_INVALIDAS
    return payload


AccessPayload = Annotated[dict[str, Any], Depends(get_access_payload)]


async def get_current_user(payload: AccessPayload, session: SessionDep) -> Usuario:
    usuario = await UsuarioRepository(session).get_by_id(uuid.UUID(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise _CREDENCIAIS_INVALIDAS
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


async def get_current_admin(usuario: CurrentUser) -> Usuario:
    if usuario.perfil != Perfil.ADMINISTRADOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )
    return usuario


CurrentAdmin = Annotated[Usuario, Depends(get_current_admin)]


def get_email_sender() -> EmailSender:
    if get_settings().smtp_host:
        return SMTPEmailSender()
    return ConsoleEmailSender()


EmailDep = Annotated[EmailSender, Depends(get_email_sender)]
