"""Convites de usuários (espelha o Invite do protótipo Django).

Admin convida por e-mail; o convidado define a própria senha ao aceitar.
Reenviar um convite cancela o anterior; o aceite respeita o limite de
usuários do plano e a unicidade de e-mail.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import Perfil, StatusConvite
from app.accounts.domain.errors import (
    ConviteInvalidoError,
    EmailJaCadastradoError,
    LimiteUsuariosAtingidoError,
)
from app.accounts.domain.password import validar_forca_senha
from app.accounts.domain.ports import EmailSender
from app.accounts.domain.rules import expirado
from app.accounts.infrastructure.models import Convite, Usuario
from app.accounts.infrastructure.repositories import (
    ConviteRepository,
    OrganizacaoRepository,
    UsuarioRepository,
)
from app.core import security
from app.core.config import get_settings


async def _verificar_limite_usuarios(session: AsyncSession, organizacao_id) -> None:
    organizacao = await OrganizacaoRepository(session).get_by_id(organizacao_id)
    if organizacao.limite_usuarios is None:
        return
    ativos = await UsuarioRepository(session).count_ativos_por_organizacao(organizacao.id)
    if ativos >= organizacao.limite_usuarios:
        raise LimiteUsuariosAtingidoError(organizacao.plano, organizacao.limite_usuarios)


async def convidar_usuario(
    session: AsyncSession,
    email_sender: EmailSender,
    *,
    admin: Usuario,
    email: str,
    perfil: Perfil,
    nome_completo: str | None = None,
) -> Convite:
    settings = get_settings()
    email = email.strip().lower()

    if await UsuarioRepository(session).get_by_email(email) is not None:
        raise EmailJaCadastradoError()
    await _verificar_limite_usuarios(session, admin.organizacao_id)

    convites = ConviteRepository(session)
    await convites.cancelar_pendentes(email, admin.organizacao_id)

    token, token_hash = security.generate_opaque_token()
    convite = Convite(
        email=email,
        nome_completo=nome_completo,
        perfil=perfil.value,
        token_hash=token_hash,
        organizacao_id=admin.organizacao_id,
        convidado_por_id=admin.id,
        expira_em=datetime.now(UTC) + timedelta(days=settings.invite_expire_days),
    )
    convites.add(convite)
    await session.commit()
    await session.refresh(convite)

    link = f"{settings.frontend_url}/aceitar-convite?token={token}"
    await email_sender.send(
        to=email,
        subject="JuriSense — Você foi convidado",
        body=(
            f"{admin.nome_completo} convidou você para a equipe no JuriSense.\n\n"
            f"Para criar sua conta, acesse: {link}\n\n"
            f"O convite expira em {settings.invite_expire_days} dias."
        ),
    )
    return convite


async def aceitar_convite(
    session: AsyncSession,
    *,
    token: str,
    senha: str,
    nome_completo: str | None = None,
) -> Usuario:
    convites = ConviteRepository(session)
    convite = await convites.get_pendente_por_hash(security.hash_opaque_token(token))
    if convite is None:
        raise ConviteInvalidoError()
    if expirado(convite.expira_em):
        convite.status = StatusConvite.EXPIRADO.value
        await session.commit()
        raise ConviteInvalidoError()

    validar_forca_senha(senha)

    usuarios = UsuarioRepository(session)
    if await usuarios.get_by_email(convite.email) is not None:
        raise EmailJaCadastradoError()
    await _verificar_limite_usuarios(session, convite.organizacao_id)

    nome = nome_completo or convite.nome_completo
    if not nome:
        raise ConviteInvalidoError()

    usuario = Usuario(
        organizacao_id=convite.organizacao_id,
        nome_completo=nome,
        email=convite.email,
        senha_hash=security.hash_password(senha),
        perfil=convite.perfil,
    )
    usuarios.add(usuario)
    await session.flush()

    convite.status = StatusConvite.ACEITO.value
    convite.aceito_por_id = usuario.id
    convite.aceito_em = datetime.now(UTC)
    await session.commit()
    await session.refresh(usuario)
    return usuario


async def listar_convites(session: AsyncSession, *, admin: Usuario) -> list[Convite]:
    return await ConviteRepository(session).list_por_organizacao(admin.organizacao_id)
