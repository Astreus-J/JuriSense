"""`SupplierEvidencePort` (docs/04-architecture/components.md rule 3): the one sanctioned
way `Policy & Compliance` reads Supplier data -- a plain application-layer function call
returning a DTO, never a cross-context ORM import. Mirrors
`supplier_service.supplier_belongs_to_organization`'s existing role as the boundary
function other contexts call into Suppliers through.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.suppliers.domain.evidence import SupplierEvidenceDTO
from app.suppliers.infrastructure.repositories import SupplierProfileRepository, SupplierRepository


async def get_normalized_profile(
    session: AsyncSession, *, organization_id: uuid.UUID, supplier_id: uuid.UUID
) -> SupplierEvidenceDTO | None:
    """Returns `None` (never raises) when the supplier doesn't exist/isn't in the
    caller's organization, or exists but has no current `SupplierProfile` yet (e.g. its
    initial `SupplierCheck` hasn't completed) -- callers (the Policy Engine's evaluation
    context builder, #60) treat a missing DTO as "no supplier evidence available," which
    the normalizer resolves into omitted `supplier.*` context fields, not a crash."""
    supplier = await SupplierRepository(session).get_by_id_and_organization(
        supplier_id, organization_id
    )
    if supplier is None:
        return None
    profile = await SupplierProfileRepository(session).get_current_by_supplier(supplier.id)
    if profile is None:
        return None
    return SupplierEvidenceDTO(
        registry_status=profile.registry_status,
        sanctions_hit=profile.sanctions_hit,
        activity_mismatch=profile.activity_mismatch,
        address_flag=profile.address_flag,
        cnae_code=profile.cnae_code,
    )
