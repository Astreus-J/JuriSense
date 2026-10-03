"""`SupplierEvidencePort` (docs/04-architecture/components.md rule 3): the one sanctioned
way `Policy & Compliance` reads Supplier data -- a plain application-layer function call
returning a DTO, never a cross-context ORM import. Mirrors
`supplier_service.supplier_belongs_to_organization`'s existing role as the boundary
function other contexts call into Suppliers through.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.suppliers.domain.evidence import SupplierCheckEvidenceDTO, SupplierEvidenceDTO
from app.suppliers.infrastructure.repositories import (
    SupplierCheckRepository,
    SupplierProfileRepository,
    SupplierRepository,
)


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


async def get_evidence_ref_for_supplier(
    session: AsyncSession, *, organization_id: uuid.UUID, supplier_id: uuid.UUID
) -> dict | None:
    """The evidence-ref counterpart to `get_normalized_profile` (Phase 5's
    `RuleEvaluation.evidence_refs` traceability, #126): every `supplier.*` context field
    comes from the same current `SupplierProfile` row (unlike Contracts' per-field
    `provenance`, `SupplierProfile` has no per-column source -- it is itself the
    normalized snapshot produced by one `SupplierCheck`), so one evidence-ref dict
    (`supplier_id`/`supplier_profile_id`/`supplier_check_id`) is traceability enough for
    any `supplier.*` path a rule references. Returns `None` under the exact same
    conditions as `get_normalized_profile` (no such supplier in this organization, or no
    current profile yet)."""
    supplier = await SupplierRepository(session).get_by_id_and_organization(
        supplier_id, organization_id
    )
    if supplier is None:
        return None
    profile = await SupplierProfileRepository(session).get_current_by_supplier(supplier.id)
    if profile is None:
        return None
    return {
        "supplier_id": str(supplier.id),
        "supplier_profile_id": str(profile.id),
        "supplier_check_id": str(profile.source_check_id),
    }


async def get_supplier_check_evidence(
    session: AsyncSession, *, organization_id: uuid.UUID, supplier_check_id: uuid.UUID
) -> SupplierCheckEvidenceDTO | None:
    """One SupplierCheck, for the Decision Passport. Returns `None` (never raises) when the
    check does not exist or its Supplier is not in the caller's organization. Checks are
    immutable once completed, so the result is the same whenever it is read."""
    check = await SupplierCheckRepository(session).get_by_id(supplier_check_id)
    if check is None:
        return None
    supplier = await SupplierRepository(session).get_by_id_and_organization(
        check.supplier_id, organization_id
    )
    if supplier is None:
        return None
    return SupplierCheckEvidenceDTO(
        supplier_check_id=check.id,
        supplier_id=check.supplier_id,
        sources_consulted=tuple(sorted(check.sources_consulted or [])),
        raw_results=dict(check.raw_results or {}),
    )
