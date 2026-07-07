import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.infrastructure.models import Acesso, Organizacao, Usuario


class UsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return await self._session.get(Usuario, usuario_id)

    def add(self, usuario: Usuario) -> None:
        self._session.add(usuario)


class OrganizacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, organizacao: Organizacao) -> None:
        self._session.add(organizacao)


class AcessoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, acesso: Acesso) -> None:
        self._session.add(acesso)
