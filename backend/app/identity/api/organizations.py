from fastapi import APIRouter

from app.core.db import SessionDep
from app.identity.api.deps import CurrentAdmin
from app.identity.api.schemas import OrganizationResponse
from app.identity.infrastructure.repositories import OrganizationRepository, UserRepository

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(admin: CurrentAdmin, session: SessionDep) -> OrganizationResponse:
    """The `/settings/organization` screen's "plan and usage" panel. Admin-only, same as
    every other endpoint in `users.py` -- matches `NAV_ITEMS.settings` being an
    admin-only nav item in the frontend (`src/lib/navigation/modules.ts`)."""
    organization = await OrganizationRepository(session).get_by_id(admin.organization_id)
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
