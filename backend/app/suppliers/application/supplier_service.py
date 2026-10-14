"""Supplier registration, listing, and status transitions (SUP-001, BR-SUP-001..003)."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.suppliers.application import check_service
from app.suppliers.domain.constants import (
    ALLOWED_STATUS_TRANSITIONS,
    SupplierCheckStatus,
    SupplierStatus,
)
from app.suppliers.domain.errors import (
    ApprovalRequiresCompletedCheckError,
    DuplicateSupplierError,
    InvalidStatusTransitionError,
    SupplierLimitExceededError,
    SupplierNotFoundError,
)
from app.suppliers.domain.tax_id import validate_tax_id
from app.suppliers.infrastructure.models import Supplier
from app.suppliers.infrastructure.repositories import (
    SupplierCheckRepository,
    SupplierProfileRepository,
    SupplierRepository,
)


def _normalize_tax_id(tax_id: str) -> str:
    """CNPJ (and, in general, jurisdiction identifiers this codebase currently supports)
    are compared digits-only so '12.345.678/0001-90' and '12345678000190' are the same
    supplier for BR-SUP-002's uniqueness check."""
    digits = "".join(ch for ch in tax_id if ch.isdigit())
    return digits or tax_id.strip()


async def create_supplier(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    legal_name: str,
    tax_id: str,
    jurisdiction: str = "BR",
) -> Supplier:
    """Registers a Supplier (SUP-001) and immediately triggers its initial
    SupplierCheck (SUP-002) — BR-SUP-001 (single organization) is enforced by always
    taking `organization_id` from the authenticated caller, never a request payload."""
    normalized_tax_id = _normalize_tax_id(tax_id)
    validate_tax_id(normalized_tax_id, jurisdiction=jurisdiction)

    suppliers = SupplierRepository(session)
    limit = get_settings().max_suppliers_per_organization
    if await suppliers.count_by_organization(organization_id) >= limit:
        raise SupplierLimitExceededError(limit)
    if (
        await suppliers.get_by_tax_id_and_organization(normalized_tax_id, organization_id)
        is not None
    ):
        raise DuplicateSupplierError(normalized_tax_id)

    supplier = Supplier(
        organization_id=organization_id,
        legal_name=legal_name,
        tax_id=normalized_tax_id,
        jurisdiction=jurisdiction,
        status=SupplierStatus.PROSPECT.value,
    )
    suppliers.add(supplier)
    try:
        await session.flush()
    except IntegrityError as exc:
        # Backstop for the DB-level unique constraint (uq_supplier_tax_id_organization)
        # in the race window between the check above and this insert — BR-SUP-002 must
        # hold even under concurrent requests, not just in the common case.
        await session.rollback()
        raise DuplicateSupplierError(normalized_tax_id) from exc

    await emit_audit_event(
        session,
        event_type="supplier.created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "supplier_id": str(supplier.id),
            "legal_name": supplier.legal_name,
            "tax_id": supplier.tax_id,
            "jurisdiction": supplier.jurisdiction,
        },
    )

    await session.commit()
    await session.refresh(supplier)

    # SUP-002: a check always starts on supplier creation. Committed before enqueueing
    # so the worker (which opens its own session) can already see the Supplier/SupplierCheck rows.
    await check_service.trigger_check(session, supplier=supplier)

    return supplier


async def list_suppliers(
    session: AsyncSession, *, organization_id: uuid.UUID, status: str | None = None
) -> list[Supplier]:
    return await SupplierRepository(session).list_by_organization(organization_id, status=status)


async def supplier_belongs_to_organization(
    session: AsyncSession, *, organization_id: uuid.UUID, supplier_id: uuid.UUID
) -> bool:
    """Cross-context ownership check for other bounded contexts that receive a caller-
    supplied `supplier_id` and need to confirm it actually belongs to the caller's own
    organization before attaching anything to it (e.g. `Contracts & Documents` creating
    a new `Contract`). Returns a bare `bool`, never the `Supplier` ORM row -- per
    `docs/04-architecture/components.md` rule 2, `Contracts & Documents` must not
    import/query Suppliers' ORM models directly; this is the sanctioned application-
    layer call instead.

    Security review (2026-09-29): `Contract` creation previously trusted the caller-
    supplied `supplier_id` outright, relying only on the FK constraint to catch a
    *nonexistent* id -- a supplier that exists but belongs to a *different* organization
    satisfied that FK just fine, letting any org attach a contract to another org's
    supplier. Confirmed live before this fix existed.
    """
    supplier = await SupplierRepository(session).get_by_id_and_organization(
        supplier_id, organization_id
    )
    return supplier is not None


async def get_supplier(
    session: AsyncSession, *, organization_id: uuid.UUID, supplier_id: uuid.UUID
) -> Supplier:
    """404 also for suppliers from other organizations (avoids leaking existence),
    mirroring `app.identity.application.user_service.get_user`."""
    supplier = await SupplierRepository(session).get_by_id_and_organization(
        supplier_id, organization_id
    )
    if supplier is None:
        raise SupplierNotFoundError()
    return supplier


async def update_supplier_status(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    supplier_id: uuid.UUID,
    new_status: SupplierStatus,
) -> Supplier:
    """BR-SUP-003 guard lives here: moving to `approved` requires at least one
    `completed` SupplierCheck, and that check's completion must be the supplier's most
    recent check activity newer than any still-open sanctions flag — i.e. the current
    SupplierProfile (built from the latest completed check) must not carry an open
    sanctions hit.
    """
    supplier = await get_supplier(session, organization_id=organization_id, supplier_id=supplier_id)
    previous_status = supplier.status

    # Security/QA review (2026-09-29): this used to accept any target status from any
    # current one (e.g. `inactive -> prospect`, `approved -> prospect`), silently
    # ignoring the documented lifecycle diagram entirely.
    allowed = ALLOWED_STATUS_TRANSITIONS[SupplierStatus(previous_status)]
    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot move a supplier from '{previous_status}' to '{new_status.value}'"
        )

    if new_status == SupplierStatus.APPROVED:
        latest_check = await SupplierCheckRepository(session).get_latest_by_supplier(supplier.id)
        if latest_check is None or latest_check.status != SupplierCheckStatus.COMPLETED.value:
            raise ApprovalRequiresCompletedCheckError()

        current_profile = await SupplierProfileRepository(session).get_current_by_supplier(
            supplier.id
        )
        if current_profile is None or current_profile.sanctions_hit:
            raise ApprovalRequiresCompletedCheckError()

    supplier.status = new_status.value

    await emit_audit_event(
        session,
        event_type="supplier.status_changed",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "supplier_id": str(supplier.id),
            "status": {"from": previous_status, "to": supplier.status},
        },
    )

    await session.commit()
    await session.refresh(supplier)
    return supplier
