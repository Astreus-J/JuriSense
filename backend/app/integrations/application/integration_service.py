"""Integration configuration-record use cases (STORY-1.4.1).

Minimal by design: this bounded context is currently a seam, not a set of real connectors
(EPIC-9 builds those later). Every use case here is a plain CRUD-on-a-config-record
operation, tenant-scoped to the caller's own organization.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.domain.errors import IntegrationNotFoundError
from app.integrations.infrastructure.models import Integration
from app.integrations.infrastructure.repositories import IntegrationRepository


async def create_integration(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    provider: str,
    config: dict[str, Any],
) -> Integration:
    integration = Integration(organization_id=organization_id, provider=provider, config=config)
    IntegrationRepository(session).add(integration)
    await session.commit()
    await session.refresh(integration)
    return integration


async def list_integrations(
    session: AsyncSession, *, organization_id: uuid.UUID
) -> list[Integration]:
    return await IntegrationRepository(session).list_by_organization(organization_id)


async def get_integration(
    session: AsyncSession, *, organization_id: uuid.UUID, integration_id: uuid.UUID
) -> Integration:
    integration = await IntegrationRepository(session).get_by_id_and_organization(
        integration_id, organization_id
    )
    if integration is None:
        raise IntegrationNotFoundError()
    return integration
