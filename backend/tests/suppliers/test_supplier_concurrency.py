"""#140: regression test for the BR-SUP-002 concurrent-creation race QA found during the
EPIC-2 round (2026-09-29) -- `create_supplier`'s IntegrityError -> DuplicateSupplierError
backstop (`supplier_service.py`) correctly converts the DB-level `uq_supplier_tax_id_
organization` violation into a 409 even when two callers' own pre-insert existence checks
both ran before either had committed. Previously proven only by a throwaway ad-hoc repro
script during the review, never by anything in the shipped suite.

True concurrency can't be reproduced hermetically against SQLite/StaticPool (same
limitation `tests/approvals/test_concurrency.py` documents for its own races) -- this
instead deterministically forces the exact interleaving a race would produce: monkeypatch
the existence check to always report "not found" (simulating two callers who both ran
that check before either row existed), then create the same Supplier twice in a row. The
first create's flush genuinely inserts the row; the second's flush hits the real unique
constraint, exercising the IntegrityError backstop exactly as a true race would.
"""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.infrastructure.repositories import UserRepository
from app.suppliers.application import supplier_service
from app.suppliers.domain.errors import DuplicateSupplierError
from app.suppliers.infrastructure.models import Supplier
from app.suppliers.infrastructure.repositories import SupplierRepository
from tests.suppliers.conftest import register_org_and_login

TAX_ID = "00000000000191"


async def test_concurrent_creation_backstop_converts_integrity_error_to_409(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await register_org_and_login(client, "supplier-race@example.com")
    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("supplier-race@example.com")
    organization_id, actor_id = admin.organization_id, admin.id

    # Simulates the race window: both "concurrent" callers' own existence check ran
    # before either had inserted, so neither sees the other's row.
    async def _always_not_found(self, tax_id: str, org_id) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(SupplierRepository, "get_by_tax_id_and_organization", _always_not_found)

    async with db_session_factory() as session:
        first = await supplier_service.create_supplier(
            session,
            organization_id=organization_id,
            actor_id=actor_id,
            legal_name="Acme Ltda",
            tax_id=TAX_ID,
            jurisdiction="BR",
        )
    assert first.tax_id == TAX_ID

    async with db_session_factory() as session:
        with pytest.raises(DuplicateSupplierError):
            await supplier_service.create_supplier(
                session,
                organization_id=organization_id,
                actor_id=actor_id,
                legal_name="Acme Ltda (duplicate)",
                tax_id=TAX_ID,
                jurisdiction="BR",
            )

    # Exactly one Supplier exists -- the second attempt's failed insert left no row
    # behind (queried directly, bypassing the monkeypatched existence check above).
    async with db_session_factory() as session:
        result = await session.execute(
            select(Supplier).where(
                Supplier.organization_id == organization_id, Supplier.tax_id == TAX_ID
            )
        )
        assert len(result.scalars().all()) == 1
