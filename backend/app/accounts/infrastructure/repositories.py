import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import StatusConvite, StatusUsuario
from app.accounts.infrastructure.models import (
    Acesso,
    Convite,
    Organizacao,
    TokenRecuperacao,
    Usuario,
)


class UsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return await self._session.get(Usuario, usuario_id)

    async def get_by_cpf(self, cpf: str) -> Usuario | None:
        result = await self._session.execute(select(Usuario).where(Usuario.cpf == cpf))
        return result.scalar_one_or_none()

    async def get_by_oab(self, oab: str, uf_oab: str) -> Usuario | None:
        result = await self._session.execute(
            select(Usuario).where(Usuario.oab == oab, Usuario.uf_oab == uf_oab)
        )
        return result.scalars().first()

    async def count_ativos_por_organizacao(self, organizacao_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(Usuario.id)).where(
                Usuario.organizacao_id == organizacao_id,
                Usuario.status == StatusUsuario.ATIVO.value,
            )
        )
        return result.scalar_one()

    async def list_por_organizacao(self, organizacao_id: uuid.UUID) -> list[Usuario]:
        result = await self._session.execute(
            select(Usuario)
            .where(Usuario.organizacao_id == organizacao_id)
            .order_by(Usuario.criado_em)
        )
        return list(result.scalars())

    def add(self, usuario: Usuario) -> None:
        self._session.add(usuario)


class TokenRecuperacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_valido_por_hash(self, token_hash: str) -> TokenRecuperacao | None:
        result = await self._session.execute(
            select(TokenRecuperacao).where(
                TokenRecuperacao.token_hash == token_hash,
                TokenRecuperacao.usado.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def invalidar_todos_do_usuario(self, usuario_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(TokenRecuperacao).where(
                TokenRecuperacao.usuario_id == usuario_id,
                TokenRecuperacao.usado.is_(False),
            )
        )
        for token in result.scalars():
            token.usado = True

    def add(self, token: TokenRecuperacao) -> None:
        self._session.add(token)


class ConviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pendente_por_hash(self, token_hash: str) -> Convite | None:
        result = await self._session.execute(
            select(Convite).where(
                Convite.token_hash == token_hash,
                Convite.status == StatusConvite.PENDENTE.value,
            )
        )
        return result.scalar_one_or_none()

    async def cancelar_pendentes(self, email: str, organizacao_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(Convite).where(
                Convite.email == email,
                Convite.organizacao_id == organizacao_id,
                Convite.status == StatusConvite.PENDENTE.value,
            )
        )
        for convite in result.scalars():
            convite.status = StatusConvite.CANCELADO.value

    async def list_por_organizacao(self, organizacao_id: uuid.UUID) -> list[Convite]:
        result = await self._session.execute(
            select(Convite)
            .where(Convite.organizacao_id == organizacao_id)
            .order_by(Convite.criado_em.desc())
        )
        return list(result.scalars())

    def add(self, convite: Convite) -> None:
        self._session.add(convite)


class OrganizacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organizacao_id: uuid.UUID) -> Organizacao | None:
        return await self._session.get(Organizacao, organizacao_id)

    def add(self, organizacao: Organizacao) -> None:
        self._session.add(organizacao)


class AcessoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, acesso: Acesso) -> None:
        self._session.add(acesso)
