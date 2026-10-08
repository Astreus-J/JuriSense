from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.db import SessionDep
from app.identity.api.deps import require_permission
from app.identity.api.schemas import OrganizationResponse
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User
from app.identity.infrastructure.repositories import OrganizationRepository, UserRepository

router = APIRouter(prefix="/organizations", tags=["organizations"])

CanReadOrganizationSettings = Annotated[
    User, Depends(require_permission(Module.ORGANIZATION_SETTINGS, "read"))
]


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    user: CanReadOrganizationSettings, session: SessionDep
) -> OrganizationResponse:
    """The `/settings/organization` screen's "plan and usage" panel. Gated on the real
    `organization_settings` RBAC grid (`DEFAULT_ROLE_GRID`), not hardcoded to admin --
    `security` also has read access to this module by design (see `rbac.py`'s table),
    unlike the user-management mutations in `users.py`, which deliberately stay
    admin-only regardless of the grid."""
    organization = await OrganizationRepository(session).get_by_id(user.organization_id)
    active_user_count = await UserRepository(session).count_active_by_organization(
        organization.id
    )
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        plan=organization.plan,
        user_limit=organization.user_limit,
        supplier_limit=organization.supplier_limit,
        storage_limit_gb=organization.storage_limit_gb,
        ai_execution_limit=organization.ai_execution_limit,
        active_user_count=active_user_count,
        created_at=organization.created_at,
    )
