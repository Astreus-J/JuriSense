import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import SessionDep
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User
from app.integrations.api.schemas import CreateIntegrationRequest, IntegrationResponse
from app.integrations.application import integration_service
from app.integrations.domain.errors import IntegrationNotFoundError

router = APIRouter(prefix="/integrations", tags=["integrations"])

CanCreateIntegrations = Annotated[User, Depends(require_permission(Module.INTEGRATIONS, "create"))]
CanReadIntegrations = Annotated[User, Depends(require_permission(Module.INTEGRATIONS, "read"))]


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    body: CreateIntegrationRequest, user: CanCreateIntegrations, session: SessionDep
) -> IntegrationResponse:
    """Gated by the caller's RBAC grid (STORY-1.1.2), not a hardcoded admin check: creates a
    configuration record only, no connector behavior (STORY-1.4.1)."""
    integration = await integration_service.create_integration(
        session,
        organization_id=user.organization_id,
        connected_by=user.id,
        provider=body.provider,
        config=body.config,
    )
    return IntegrationResponse.model_validate(integration)


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    user: CanReadIntegrations, session: SessionDep
) -> list[IntegrationResponse]:
    integrations = await integration_service.list_integrations(
        session, organization_id=user.organization_id
    )
    return [IntegrationResponse.model_validate(i) for i in integrations]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: uuid.UUID, user: CanReadIntegrations, session: SessionDep
) -> IntegrationResponse:
    try:
        integration = await integration_service.get_integration(
            session, organization_id=user.organization_id, integration_id=integration_id
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return IntegrationResponse.model_validate(integration)
