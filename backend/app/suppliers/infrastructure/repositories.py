import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.suppliers.domain.constants import SupplierCheckStatus
from app.suppliers.infrastructure.models import Supplier, SupplierCheck, SupplierProfile


class SupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, supplier: Supplier) -> None:
        self._session.add(supplier)

    async def get_by_id_and_organization(
        self, supplier_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Supplier | None:
        """Tenant-scoped lookup: an id from another organization resolves to None, never
        a 403 (`app.identity.application.user_service.get_user`'s pattern — avoids
        confirming cross-tenant existence)."""
        result = await self._session.execute(
            select(Supplier).where(
                Supplier.id == supplier_id, Supplier.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tax_id_and_organization(
        self, tax_id: str, organization_id: uuid.UUID
    ) -> Supplier | None:
        result = await self._session.execute(
            select(Supplier).where(
                Supplier.tax_id == tax_id, Supplier.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[Supplier]:
        query = select(Supplier).where(Supplier.organization_id == organization_id)
        if status is not None:
            query = query.where(Supplier.status == status)
        result = await self._session.execute(query.order_by(Supplier.created_at))
        return list(result.scalars())


class SupplierCheckRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, check: SupplierCheck) -> None:
        self._session.add(check)

    async def get_by_id(self, check_id: uuid.UUID) -> SupplierCheck | None:
        return await self._session.get(SupplierCheck, check_id)

    async def list_by_supplier(self, supplier_id: uuid.UUID) -> list[SupplierCheck]:
        """Full, immutable check history (SUP-005), most recent first."""
        result = await self._session.execute(
            select(SupplierCheck)
            .where(SupplierCheck.supplier_id == supplier_id)
            .order_by(SupplierCheck.started_at.desc())
        )
        return list(result.scalars())

    async def get_latest_by_supplier(self, supplier_id: uuid.UUID) -> SupplierCheck | None:
        result = await self._session.execute(
            select(SupplierCheck)
            .where(SupplierCheck.supplier_id == supplier_id)
            .order_by(SupplierCheck.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_completed(self, check: SupplierCheck, *, raw_results: dict) -> None:
        """The one completion write a `SupplierCheck` ever receives — the row is
        immutable afterward (domain-model.md). Guards against being called twice, which
        would otherwise silently rewrite supposedly-immutable history."""
        if check.status != SupplierCheckStatus.STARTED.value:
            raise ValueError(f"Cannot complete a check already in status '{check.status}'")
        check.status = SupplierCheckStatus.COMPLETED.value
        check.raw_results = raw_results
        check.completed_at = datetime.now(UTC)

    async def mark_failed(self, check: SupplierCheck, *, raw_results: dict, reason: str) -> None:
        if check.status != SupplierCheckStatus.STARTED.value:
            raise ValueError(f"Cannot fail a check already in status '{check.status}'")
        check.status = SupplierCheckStatus.FAILED.value
        check.raw_results = raw_results
        check.failure_reason = reason
        check.completed_at = datetime.now(UTC)


class SupplierProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_by_supplier(self, supplier_id: uuid.UUID) -> SupplierProfile | None:
        result = await self._session.execute(
            select(SupplierProfile).where(
                SupplierProfile.supplier_id == supplier_id, SupplierProfile.is_current.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def replace_current(self, new_profile: SupplierProfile) -> None:
        """Replaces (never mutates) the current profile: supersedes any existing
        `is_current=True` row for this supplier, then inserts `new_profile` as the new
        current one, in the same transaction — matching domain-model.md's "replaced
        (not mutated) on every successful re-check".

        This application-level supersede-then-insert is the primary enforcement of "one
        current profile per supplier"; the partial unique index on `SupplierProfile` is
        defense-in-depth, not the only guard, because a cross-request race would need a
        DB-level `SELECT ... FOR UPDATE` on the supplier row to close entirely, which is
        out of scope for this phase (only one Celery worker processes any given
        `SupplierCheck`, so the practical race window is negligible).
        """
        await self._session.execute(
            update(SupplierProfile)
            .where(
                SupplierProfile.supplier_id == new_profile.supplier_id,
                SupplierProfile.is_current.is_(True),
            )
            .values(is_current=False, superseded_at=datetime.now(UTC))
        )
        self._session.add(new_profile)
