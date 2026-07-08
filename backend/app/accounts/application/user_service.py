"""Casos de uso de gestão de usuários pela organização (RF04, parcial).

Espelha o CreateUserUseCase do protótipo Django: só administradores criam
usuários, sempre na própria organização, respeitando o limite de usuários
ativos do plano e a unicidade de e-mail, CPF e OAB.
"""

import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import Perfil, StatusUsuario
from app.accounts.domain.errors import (
    CpfJaCadastradoError,
    EmailJaCadastradoError,
    LimiteUsuariosAtingidoError,
    OabJaCadastradaError,
    OperacaoNaoPermitidaError,
    UsuarioNaoEncontradoError,
)
from app.accounts.domain.password import validar_forca_senha
from app.accounts.domain.rules import validar_formato_oab
from app.accounts.infrastructure.models import Usuario
from app.accounts.infrastructure.repositories import OrganizacaoRepository, UsuarioRepository
from app.accounts.infrastructure.token_store import TokenStore
from app.core import security


async def criar_usuario(
    session: AsyncSession,
    *,
    admin: Usuario,
    nome_completo: str,
    email: str,
    senha: str,
    perfil: Perfil,
    oab: str | None = None,
    uf_oab: str | None = None,
    cpf: str | None = None,
    telefone: str | None = None,
) -> Usuario:
    """Cria um usuário na organização do admin autenticado.

    A organização de destino vem SEMPRE do admin autenticado, nunca do payload.
    """
    email = email.strip().lower()
    validar_forca_senha(senha)
    if oab is not None:
        validar_formato_oab(oab, uf_oab)

    organizacao = await OrganizacaoRepository(session).get_by_id(admin.organizacao_id)
    usuarios = UsuarioRepository(session)

    if organizacao.limite_usuarios is not None:
        ativos = await usuarios.count_ativos_por_organizacao(organizacao.id)
        if ativos >= organizacao.limite_usuarios:
            raise LimiteUsuariosAtingidoError(organizacao.plano, organizacao.limite_usuarios)

    if await usuarios.get_by_email(email) is not None:
        raise EmailJaCadastradoError()
    if cpf is not None and await usuarios.get_by_cpf(cpf) is not None:
        raise CpfJaCadastradoError()
    if oab is not None and uf_oab is not None and await usuarios.get_by_oab(oab, uf_oab):
        raise OabJaCadastradaError()

    usuario = Usuario(
        organizacao_id=admin.organizacao_id,
        nome_completo=nome_completo,
        email=email,
        senha_hash=security.hash_password(senha),
        perfil=perfil.value,
        oab=oab,
        uf_oab=uf_oab,
        cpf=cpf,
        telefone=telefone,
    )
    usuarios.add(usuario)
    await session.commit()
    await session.refresh(usuario)
    return usuario


async def listar_usuarios(session: AsyncSession, *, admin: Usuario) -> list[Usuario]:
    return await UsuarioRepository(session).list_por_organizacao(admin.organizacao_id)


async def obter_usuario(
    session: AsyncSession, *, admin: Usuario, usuario_id: uuid.UUID
) -> Usuario:
    """404 também para usuários de outras organizações (sem vazar existência)."""
    usuario = await UsuarioRepository(session).get_by_id(usuario_id)
    if usuario is None or usuario.organizacao_id != admin.organizacao_id:
        raise UsuarioNaoEncontradoError()
    return usuario


async def atualizar_usuario(
    session: AsyncSession,
    *,
    admin: Usuario,
    usuario_id: uuid.UUID,
    campos: dict,
) -> Usuario:
    usuario = await obter_usuario(session, admin=admin, usuario_id=usuario_id)

    if usuario.id == admin.id and ("perfil" in campos or "status" in campos):
        raise OperacaoNaoPermitidaError(
            "Administrador não pode alterar o próprio perfil ou status"
        )

    if "oab" in campos or "uf_oab" in campos:
        oab = campos.get("oab", usuario.oab)
        uf_oab = campos.get("uf_oab", usuario.uf_oab)
        if oab is not None:
            validar_formato_oab(oab, uf_oab)
            existente = await UsuarioRepository(session).get_by_oab(oab, uf_oab)
            if existente is not None and existente.id != usuario.id:
                raise OabJaCadastradaError()

    if campos.get("cpf") is not None and campos["cpf"] != usuario.cpf:
        existente = await UsuarioRepository(session).get_by_cpf(campos["cpf"])
        if existente is not None:
            raise CpfJaCadastradoError()

    # Reativação volta a contar no limite do plano
    if campos.get("status") == StatusUsuario.ATIVO.value and not usuario.ativo:
        organizacao = await OrganizacaoRepository(session).get_by_id(admin.organizacao_id)
        if organizacao.limite_usuarios is not None:
            ativos = await UsuarioRepository(session).count_ativos_por_organizacao(
                organizacao.id
            )
            if ativos >= organizacao.limite_usuarios:
                raise LimiteUsuariosAtingidoError(organizacao.plano, organizacao.limite_usuarios)

    for campo, valor in campos.items():
        setattr(usuario, campo, valor.value if hasattr(valor, "value") else valor)

    await session.commit()
    await session.refresh(usuario)
    return usuario


async def desativar_usuario(
    session: AsyncSession,
    redis: aioredis.Redis,
    *,
    admin: Usuario,
    usuario_id: uuid.UUID,
) -> None:
    """Desativação lógica (RF04: sem exclusão física) + revogação das sessões."""
    usuario = await obter_usuario(session, admin=admin, usuario_id=usuario_id)
    if usuario.id == admin.id:
        raise OperacaoNaoPermitidaError("Administrador não pode desativar a própria conta")

    usuario.status = StatusUsuario.INATIVO.value
    await session.commit()
    await TokenStore(redis).revoke_all_refresh_for_user(str(usuario.id))
