"""Casos de uso de gestão de usuários pela organização (RF04, parcial).

Espelha o CreateUserUseCase do protótipo Django: só administradores criam
usuários, sempre na própria organização, respeitando o limite de usuários
ativos do plano e a unicidade de e-mail, CPF e OAB.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import Perfil
from app.accounts.domain.errors import (
    CpfJaCadastradoError,
    EmailJaCadastradoError,
    LimiteUsuariosAtingidoError,
    OabJaCadastradaError,
)
from app.accounts.domain.password import validar_forca_senha
from app.accounts.infrastructure.models import Usuario
from app.accounts.infrastructure.repositories import OrganizacaoRepository, UsuarioRepository
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
