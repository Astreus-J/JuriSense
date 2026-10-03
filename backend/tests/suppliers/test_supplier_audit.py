"""FEATURE-7.2 / STORY-7.2.1: AuditEvents for Supplier creation, status changes, and the
SupplierCheck lifecycle (started, completed, failed) plus the profile it materializes [AUD-001].
"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.models import AuditEvent
from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login

TAX_ID = "00000000000191"


async def _create_supplier(client: httpx.AsyncClient, headers: dict) -> dict:
    created = await client.post(
        "/api/suppliers",
        json={"legal_name": "Banco do Brasil SA", "tax_id": TAX_ID, "jurisdiction": "BR"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return created.json()


async def _org_and_user(db_session_factory: async_sessionmaker, email: str):
    async with db_session_factory() as session:
        return await UserRepository(session).get_by_email(email)


async def _events(db_session_factory: async_sessionmaker, event_type: str) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(event_type=event_type)


async def test_supplier_creation_emits_supplier_created(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, "audit-supplier-created@example.com")
    supplier = await _create_supplier(client, headers)
    admin = await _org_and_user(db_session_factory, "audit-supplier-created@example.com")

    [event] = await _events(db_session_factory, "supplier.created")
    assert event.actor_id == admin.id
    assert event.organization_id == admin.organization_id
    assert event.payload["supplier_id"] == supplier["id"]


async def test_status_change_emits_supplier_status_changed(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, "audit-supplier-status@example.com")
    supplier = await _create_supplier(client, headers)

    changed = await client.patch(
        f"/api/suppliers/{supplier['id']}/status", json={"status": "blocked"}, headers=headers
    )
    assert changed.status_code == 200, changed.text

    [event] = await _events(db_session_factory, "supplier.status_changed")
    assert event.payload["supplier_id"] == supplier["id"]
    assert event.payload["status"] == {"from": "prospect", "to": "blocked"}


async def test_creation_starts_a_check_and_emits_supplier_check_started(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, "audit-check-started@example.com")
    supplier = await _create_supplier(client, headers)

    [event] = await _events(db_session_factory, "supplier.check.started")
    checks = (await client.get(f"/api/suppliers/{supplier['id']}/checks", headers=headers)).json()
    assert event.payload["supplier_id"] == supplier["id"]
    assert event.payload["check_id"] == checks[0]["id"]


async def test_completed_check_emits_completed_and_profile_updated(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, "audit-check-completed@example.com")
    supplier = await _create_supplier(client, headers)
    checks = (await client.get(f"/api/suppliers/{supplier['id']}/checks", headers=headers)).json()
    check_id = checks[0]["id"]

    [completed] = await _events(db_session_factory, "supplier.check.completed")
    [profile] = await _events(db_session_factory, "supplier.profile_updated")
    assert completed.payload == {"supplier_id": supplier["id"], "check_id": check_id}
    assert profile.payload["supplier_id"] == supplier["id"]
    assert profile.payload["sanctions_hit"] is False
    assert "registry_status" in profile.payload


async def test_check_with_unavailable_mandatory_source_emits_supplier_check_failed(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_cnpj_registry(unavailable=True)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, "audit-check-failed@example.com")
    supplier = await _create_supplier(client, headers)
    checks = (await client.get(f"/api/suppliers/{supplier['id']}/checks", headers=headers)).json()

    [event] = await _events(db_session_factory, "supplier.check.failed")
    assert event.actor_id is None
    assert event.payload["supplier_id"] == supplier["id"]
    assert event.payload["check_id"] == checks[0]["id"]
    assert event.payload["reason"]
    assert await _events(db_session_factory, "supplier.check.completed") == []
    assert (
        await _org_and_user(db_session_factory, "audit-check-failed@example.com")
    ).organization_id == event.organization_id


async def test_every_supplier_event_is_tenant_scoped(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """A supplier event never lands under another organization's id."""
    headers = await register_org_and_login(client, "audit-supplier-tenant@example.com")
    await _create_supplier(client, headers)
    org_id = (
        await _org_and_user(db_session_factory, "audit-supplier-tenant@example.com")
    ).organization_id

    async with db_session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(AuditEvent).where(AuditEvent.event_type.like("supplier.%"))
                )
            )
            .scalars()
            .all()
        )
    assert rows
    assert {row.organization_id for row in rows} == {org_id}
