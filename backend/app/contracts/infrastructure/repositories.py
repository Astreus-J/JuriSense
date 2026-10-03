import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.domain.constants import ContractVersionStatus
from app.contracts.infrastructure.models import Clause, Contract, ContractVersion, Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(document)

    async def get_by_id_and_organization(
        self, document_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Document | None:
        result = await self._session.execute(
            select(Document).where(
                Document.id == document_id, Document.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()


class ContractRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, contract: Contract) -> None:
        self._session.add(contract)

    async def get_by_id_and_organization(
        self, contract_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Contract | None:
        result = await self._session.execute(
            select(Contract).where(
                Contract.id == contract_id, Contract.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Contract]:
        result = await self._session.execute(
            select(Contract)
            .where(Contract.organization_id == organization_id)
            .order_by(Contract.created_at)
        )
        return list(result.scalars())


class ContractVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, version: ContractVersion) -> None:
        self._session.add(version)

    async def get_by_id(self, version_id: uuid.UUID) -> ContractVersion | None:
        return await self._session.get(ContractVersion, version_id)

    async def get_next_version_number(self, contract_id: uuid.UUID) -> int:
        """BR-CON-002: every negotiation round gets a strictly increasing version
        number; existing versions are never renumbered or edited."""
        result = await self._session.execute(
            select(func.max(ContractVersion.version_number)).where(
                ContractVersion.contract_id == contract_id
            )
        )
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    async def list_by_contract(self, contract_id: uuid.UUID) -> list[ContractVersion]:
        result = await self._session.execute(
            select(ContractVersion)
            .where(ContractVersion.contract_id == contract_id)
            .order_by(ContractVersion.version_number.desc())
        )
        return list(result.scalars())

    async def get_newest_analyzed_after(
        self, contract_id: uuid.UUID, version_number: int
    ) -> uuid.UUID | None:
        """The highest-numbered `analyzed` ContractVersion of this Contract whose
        `version_number` is strictly greater than `version_number` -- `None` if there is
        none. Used by Policy & Compliance's re-evaluation staleness check (FEATURE-6.4)."""
        result = await self._session.execute(
            select(ContractVersion.id)
            .where(
                ContractVersion.contract_id == contract_id,
                ContractVersion.status == ContractVersionStatus.ANALYZED.value,
                ContractVersion.version_number > version_number,
            )
            .order_by(ContractVersion.version_number.desc())
            .limit(1)
        )
        return result.scalars().first()


class ClauseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, clause: Clause) -> None:
        self._session.add(clause)

    async def list_by_contract_version(self, contract_version_id: uuid.UUID) -> list[Clause]:
        result = await self._session.execute(
            select(Clause)
            .where(Clause.contract_version_id == contract_version_id)
            .order_by(Clause.page, Clause.id)
        )
        return list(result.scalars())
