"""Recuperação de senha (RF02) — espelha o fluxo do protótipo Django.

Token single-use com expiração de 1h; a resposta nunca revela se o e-mail
existe; após a troca, todas as sessões do usuário são revogadas (MED-001)
e ele é notificado por e-mail.
"""

from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.errors import TokenRecuperacaoInvalidoError
from app.accounts.domain.password import validar_forca_senha
from app.accounts.domain.ports import EmailSender
from app.accounts.domain.rules import expirado
from app.accounts.infrastructure.models import TokenRecuperacao
from app.accounts.infrastructure.repositories import (
    TokenRecuperacaoRepository,
    UsuarioRepository,
)
from app.accounts.infrastructure.token_store import TokenStore
from app.core import security
from app.core.config import get_settings


async def solicitar_recuperacao(
    session: AsyncSession, email_sender: EmailSender, *, email: str
) -> None:
    """Sempre silencioso: quem chama responde genérico, exista o e-mail ou não."""
    settings = get_settings()
    email = email.strip().lower()

    usuario = await UsuarioRepository(session).get_by_email(email)
    if usuario is None or not usuario.ativo:
        return

    tokens = TokenRecuperacaoRepository(session)
    await tokens.invalidar_todos_do_usuario(usuario.id)

    token, token_hash = security.generate_opaque_token()
    tokens.add(
        TokenRecuperacao(
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_em=datetime.now(UTC)
            + timedelta(minutes=settings.password_reset_expire_minutes),
        )
    )
    await session.commit()

    link = f"{settings.frontend_url}/redefinir-senha?token={token}"
    await email_sender.send(
        to=email,
        subject="JuriSense — Recuperação de senha",
        body=(
            f"Olá, {usuario.nome_completo}.\n\n"
            f"Para redefinir sua senha, acesse: {link}\n\n"
            f"O link expira em {settings.password_reset_expire_minutes} minutos. "
            "Se você não solicitou a recuperação, ignore este e-mail."
        ),
    )


async def redefinir_senha(
    session: AsyncSession,
    redis: aioredis.Redis,
    email_sender: EmailSender,
    *,
    token: str,
    nova_senha: str,
) -> None:
    validar_forca_senha(nova_senha)

    registro = await TokenRecuperacaoRepository(session).get_valido_por_hash(
        security.hash_opaque_token(token)
    )
    if registro is None or expirado(registro.expira_em):
        raise TokenRecuperacaoInvalidoError()

    usuario = await UsuarioRepository(session).get_by_id(registro.usuario_id)
    if usuario is None or not usuario.ativo:
        raise TokenRecuperacaoInvalidoError()

    usuario.senha_hash = security.hash_password(nova_senha)
    registro.usado = True
    await session.commit()

    # Sessões antigas deixam de valer (MED-001)
    await TokenStore(redis).revoke_all_refresh_for_user(str(usuario.id))

    await email_sender.send(
        to=usuario.email,
        subject="JuriSense — Sua senha foi alterada",
        body=(
            f"Olá, {usuario.nome_completo}.\n\n"
            "A senha da sua conta foi alterada e todas as sessões ativas foram "
            "encerradas. Se não foi você, entre em contato com o suporte imediatamente."
        ),
    )
