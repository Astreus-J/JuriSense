"""`ContractEvidencePort` (docs/04-architecture/components.md rule 3): the one sanctioned
way `Policy & Compliance` reads Contract/extraction data -- a plain application-layer
function call returning a DTO, never a cross-context ORM import. Mirrors
`app.suppliers.application.evidence_service.get_normalized_profile`.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.domain.evidence import (
    ContractEvidenceDTO,
    contract_fields_to_evidence_dto,
    contract_fields_to_evidence_refs,
)
from app.contracts.infrastructure.repositories import ContractRepository, ContractVersionRepository


async def get_normalized_terms(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> ContractEvidenceDTO | None:
    """Returns `None` (never raises) when the `ContractVersion` doesn't exist, its parent
    `Contract` isn't in the caller's organization, or extraction hasn't produced any
    fields yet -- same "missing evidence, not an error" contract as
    `SupplierEvidencePort.get_normalized_profile`."""
    version = await ContractVersionRepository(session).get_by_id(contract_version_id)
    if version is None:
        return None
    # Tenant check: `ContractVersion` has no `organization_id` column of its own (it
    # belongs to a `Contract`, which does) -- confirm ownership via the parent, never by
    # trusting a caller-supplied id outright (the same class of gap
    # `supplier_belongs_to_organization`'s docstring documents having previously existed
    # for `Contract` creation).
    contract = await ContractRepository(session).get_by_id_and_organization(
        version.contract_id, organization_id
    )
    if contract is None:
        return None
    fields = (version.extracted_data or {}).get("fields")
    if not isinstance(fields, dict):
        return None
    return contract_fields_to_evidence_dto(fields)


async def get_supplier_id_for_contract_version(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> uuid.UUID | None:
    """Resolves the `Supplier` a `ContractVersion` belongs to (via its `Contract`), so a
    caller building a combined supplier+contract evaluation context (#60) knows which
    `supplier_id` to pass to `SupplierEvidencePort`. `Contract.supplier_id` is
    `Contracts & Documents`' own data (a plain FK value, per
    `docs/04-architecture/components.md` rule 2) -- this is the sanctioned
    application-layer way for `Policy & Compliance` to read it, rather than importing
    `Contract`'s ORM model directly."""
    version = await ContractVersionRepository(session).get_by_id(contract_version_id)
    if version is None:
        return None
    contract = await ContractRepository(session).get_by_id_and_organization(
        version.contract_id, organization_id
    )
    if contract is None:
        return None
    return contract.supplier_id


async def contract_version_belongs_to_organization(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> bool:
    """Existence+ownership check independent of extraction state -- unlike
    `get_normalized_terms` (which also returns falsy when extraction simply hasn't
    finished yet), this distinguishes "contract version genuinely doesn't exist / isn't
    ours" from "exists, but no extracted evidence yet". The trigger-review use case
    (#123) 404s only on the former; the latter is a valid state to trigger a review in --
    `contract.*` rules simply come back `NOT_APPLICABLE` (BR-CMP-001)."""
    version = await ContractVersionRepository(session).get_by_id(contract_version_id)
    if version is None:
        return False
    contract = await ContractRepository(session).get_by_id_and_organization(
        version.contract_id, organization_id
    )
    return contract is not None


async def get_evidence_refs_for_contract_version(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> dict[str, dict]:
    """Returns the `contract.*` evidence-ref map (`contract_fields_to_evidence_refs`) for
    one `ContractVersion` -- empty (never `None`) when the version doesn't resolve or has
    no extracted fields yet, so callers (`compliance_review_service`'s evidence-ref
    assembly, #126) can use it unconditionally as a lookup dict."""
    version = await ContractVersionRepository(session).get_by_id(contract_version_id)
    if version is None:
        return {}
    contract = await ContractRepository(session).get_by_id_and_organization(
        version.contract_id, organization_id
    )
    if contract is None:
        return {}
    fields = (version.extracted_data or {}).get("fields")
    if not isinstance(fields, dict):
        return {}
    return contract_fields_to_evidence_refs(fields)
