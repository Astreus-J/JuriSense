import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.domain.constants import StatusUsuario
from app.accounts.infrastructure.models import Acesso, Organizacao, Usuario


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

    def add(self, usuario: Usuario) -> None:
        self._session.add(usuario)


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
