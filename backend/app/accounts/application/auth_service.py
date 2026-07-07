"""Casos de uso de autenticação: registro, login, refresh e logout."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import LIMITES_POR_PLANO, Perfil, Plano
from app.accounts.domain.errors import (
    ContaBloqueadaError,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    RefreshTokenInvalidoError,
    UsuarioInativoError,
)
from app.accounts.domain.password import validar_forca_senha
from app.accounts.infrastructure.lockout import LoginLockout
from app.accounts.infrastructure.models import Acesso, Organizacao, Usuario
from app.accounts.infrastructure.repositories import (
    AcessoRepository,
    OrganizacaoRepository,
    UsuarioRepository,
)
from app.accounts.infrastructure.token_store import TokenStore
from app.core import security
from app.core.config import get_settings


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def _lockout(redis: aioredis.Redis) -> LoginLockout:
    settings = get_settings()
    return LoginLockout(
        redis,
        max_attempts=settings.login_max_attempts,
        lockout_seconds=settings.login_lockout_minutes * 60,
    )


async def _emitir_tokens(redis: aioredis.Redis, usuario_id: uuid.UUID) -> TokenPair:
    settings = get_settings()
    access_token, _ = security.create_access_token(usuario_id)
    refresh_token, refresh_jti = security.create_refresh_token(usuario_id)
    await TokenStore(redis).store_refresh(
        refresh_jti,
        str(usuario_id),
        ttl_seconds=settings.refresh_token_expire_days * 24 * 3600,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def registrar_organizacao(
    session: AsyncSession,
    *,
    organizacao_nome: str,
    nome_completo: str,
    email: str,
    senha: str,
    oab: str | None = None,
    uf_oab: str | None = None,
    cpf: str | None = None,
    telefone: str | None = None,
    plano: Plano = Plano.AUTONOMO,
) -> Usuario:
    """Cria a organização (com os limites do plano escolhido) e seu admin."""
    email = _normalizar_email(email)
    validar_forca_senha(senha)

    usuarios = UsuarioRepository(session)
    if await usuarios.get_by_email(email) is not None:
        raise EmailJaCadastradoError()

    limites = LIMITES_POR_PLANO[plano]
    organizacao = Organizacao(
        nome=organizacao_nome,
        plano=plano.value,
        limite_usuarios=limites.usuarios,
        limite_processos=limites.processos_ativos,
        limite_armazenamento_gb=limites.armazenamento_gb,
        limite_geracoes_ia_mes=limites.geracoes_ia_mes,
    )
    OrganizacaoRepository(session).add(organizacao)

    admin = Usuario(
        organizacao=organizacao,
        nome_completo=nome_completo,
        email=email,
        senha_hash=security.hash_password(senha),
        oab=oab,
        uf_oab=uf_oab,
        cpf=cpf,
        telefone=telefone,
        perfil=Perfil.ADMINISTRADOR.value,
    )
    usuarios.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def login(
    session: AsyncSession,
    redis: aioredis.Redis,
    *,
    email: str,
    senha: str,
    ip: str | None,
    user_agent: str | None,
) -> TokenPair:
    email = _normalizar_email(email)
    lockout = _lockout(redis)

    retry_after = await lockout.seconds_until_unlock(email)
    if retry_after is not None:
        raise ContaBloqueadaError(retry_after)

    usuario = await UsuarioRepository(session).get_by_email(email)

    async def _falha() -> None:
        await lockout.register_failure(email)
        AcessoRepository(session).add(
            Acesso(
                usuario_id=usuario.id if usuario else None,
                email=email,
                ip=ip,
                user_agent=user_agent,
                sucesso=False,
            )
        )
        await session.commit()

    if usuario is None:
        security.verify_dummy_password(senha)
        await _falha()
        raise CredenciaisInvalidasError()

    if not security.verify_password(senha, usuario.senha_hash):
        await _falha()
        raise CredenciaisInvalidasError()

    if not usuario.ativo:
        raise UsuarioInativoError()

    await lockout.reset(email)
    usuario.ultimo_acesso = datetime.now(UTC)
    AcessoRepository(session).add(
        Acesso(usuario_id=usuario.id, email=email, ip=ip, user_agent=user_agent, sucesso=True)
    )
    await session.commit()
    return await _emitir_tokens(redis, usuario.id)


async def renovar_tokens(
    session: AsyncSession, redis: aioredis.Redis, *, refresh_token: str
) -> TokenPair:
    """Rotação de refresh token: o token usado é invalidado e um novo par é emitido."""
    try:
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN)
    except security.TokenError as exc:
        raise RefreshTokenInvalidoError() from exc

    user_id = await TokenStore(redis).consume_refresh(payload["jti"])
    if user_id is None or user_id != payload["sub"]:
        raise RefreshTokenInvalidoError()

    usuario = await UsuarioRepository(session).get_by_id(uuid.UUID(user_id))
    if usuario is None or not usuario.ativo:
        raise RefreshTokenInvalidoError()

    return await _emitir_tokens(redis, usuario.id)


async def logout(
    redis: aioredis.Redis, *, access_payload: dict, refresh_token: str | None
) -> None:
    """Revoga o refresh token e bloqueia o access token até expirar."""
    store = TokenStore(redis)

    exp = datetime.fromtimestamp(access_payload["exp"], tz=UTC)
    restante = int((exp - datetime.now(UTC)).total_seconds())
    await store.block_access(access_payload["jti"], restante)

    if refresh_token is None:
        return
    try:
        payload = security.decode_token(refresh_token, security.REFRESH_TOKEN)
    except security.TokenError:
        return  # refresh já inválido; nada a revogar
    if payload["sub"] == access_payload["sub"]:
        await store.revoke_refresh(payload["jti"])
