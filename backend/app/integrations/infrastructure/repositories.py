import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.infrastructure.models import Integration


class IntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_and_organization(
        self, integration_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Integration | None:
        """Tenant-scoped lookup: an id from another organization resolves to None, never a
        403 (avoids confirming cross-tenant existence — `docs/07-engineering/coding-standards.md`).
        """
        result = await self._session.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Integration]:
        result = await self._session.execute(
            select(Integration)
            .where(Integration.organization_id == organization_id)
            .order_by(Integration.created_at)
        )
        return list(result.scalars())

    def add(self, integration: Integration) -> None:
        self._session.add(integration)
