"""Integration configuration-record use cases (STORY-1.4.1).

Minimal by design: this bounded context is currently a seam, not a set of real connectors
(EPIC-9 builds those later). Every use case here is a plain CRUD-on-a-config-record
operation, tenant-scoped to the caller's own organization.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.audit_service import emit_audit_event
from app.integrations.domain.errors import IntegrationNotFoundError
from app.integrations.infrastructure.credential_encryption import encrypt_integration_config
from app.integrations.infrastructure.models import Integration
from app.integrations.infrastructure.repositories import IntegrationRepository


async def create_integration(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    connected_by: uuid.UUID,
    provider: str,
    config: dict[str, Any],
) -> Integration:
    # Credential-like values (same key-matching rule as the H1 masking fix) are encrypted
    # before this ever reaches the database -- see credential_encryption.py.
    integration = Integration(
        organization_id=organization_id,
        provider=provider,
        config=encrypt_integration_config(config),
    )
    IntegrationRepository(session).add(integration)
    await session.flush()  # populate integration.id for the audit payload below
    # Payload carries the provider only: `config` may hold connector credentials.
    await emit_audit_event(
        session,
        event_type="integration.connected",
        actor_id=connected_by,
        organization_id=organization_id,
        payload={
            "integration_id": str(integration.id),
            "organization_id": str(organization_id),
            "provider": provider,
            "connected_by": str(connected_by),
            "connected_at": datetime.now(UTC).isoformat(),
        },
    )
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
