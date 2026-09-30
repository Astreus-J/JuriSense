"""Human confirmation of a low-confidence `ContractVersion` (CON-005, BR-CON-003).

Backend endpoint only -- the frontend confirmation UI is separate scope (see the EPIC-3
brief). A `ContractVersion` in `needs_confirmation` cannot reach `analyzed` any other way.
"""

import copy
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.domain.constants import ContractVersionStatus
from app.contracts.domain.errors import (
    ContractVersionNotReadyForConfirmationError,
)
from app.contracts.domain.extracted_data import apply_confirmation
from app.contracts.infrastructure.models import ContractVersion
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event


async def confirm_contract_version(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    contract_version: ContractVersion,
    corrections: dict[str, Any] | None = None,
) -> ContractVersion:
    """`corrections` maps a dotted field path (as produced by
    `app.contracts.domain.extracted_data.iter_field_leaves`, e.g. `"liability.type"`) to
    a corrected value. A low-confidence field with no entry in `corrections` is confirmed
    as-is (the AI-extracted value is accepted, not changed) -- either way it is stamped
    `human_confirmed` (contract-compliance.md: "preserving an honest provenance trail"),
    never silently promoted to look like a high-confidence AI extraction.
    """
    if contract_version.status != ContractVersionStatus.NEEDS_CONFIRMATION.value:
        raise ContractVersionNotReadyForConfirmationError(contract_version.status)

    settings = get_settings()
    # Deep-copied, never mutated in place: `apply_confirmation` mutates the nested
    # leaf dicts it's given, and a plain (non-`Mutable`-wrapped) JSON column's dirty
    # check compares the old vs. new value by equality -- if the "old" cached reference
    # and the "new" value shared the same nested (in-place-mutated) sub-dict objects,
    # they would compare equal even though the content changed, and SQLAlchemy would
    # silently drop `extracted_data` from the UPDATE entirely. Deep-copying first keeps
    # the original, still-`committed_state`-referenced dict genuinely untouched, so the
    # new value is a real, detectable difference.
    fields = copy.deepcopy(contract_version.extracted_data.get("fields", {}))
    apply_confirmation(
        fields,
        corrections=corrections or {},
        threshold=settings.contract_extraction_confidence_threshold,
    )
    contract_version.extracted_data = {**contract_version.extracted_data, "fields": fields}
    contract_version.status = ContractVersionStatus.ANALYZED.value

    await emit_audit_event(
        session,
        event_type="contract.version_confirmed",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "contract_id": str(contract_version.contract_id),
            "contract_version_id": str(contract_version.id),
            "corrected_fields": sorted((corrections or {}).keys()),
        },
    )
    await emit_audit_event(
        session,
        event_type="contract.analysis_completed",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "contract_id": str(contract_version.contract_id),
            "contract_version_id": str(contract_version.id),
            "via_human_confirmation": True,
        },
    )

    await session.commit()
    await session.refresh(contract_version)
    return contract_version
