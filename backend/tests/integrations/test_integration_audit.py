"""FEATURE-7.2 / STORY-7.2.1: creating an Integration emits integration.connected [AUD-001],
in the same transaction as the record, with a payload that never carries its config."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from app.integrations.application import integration_service

EMAIL = "admin-audit-int@example.com"


async def _admin_headers(client: httpx.AsyncClient) -> dict:
    await client.post(
        "/api/auth/register",
        json={
            "organization_name": "Audit Integrations Org",
            "full_name": "Admin",
            "email": EMAIL,
            "password": "StrongPass1",
            "plan": "business",
        },
    )
    login = await client.post("/api/auth/login", json={"email": EMAIL, "password": "StrongPass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_integration_emits_integration_connected(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await _admin_headers(client)
    created = await client.post(
        "/api/integrations",
        json={"provider": "docusign", "config": {"api_key": "super-secret-value"}},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email(EMAIL)
        events = await AuditEventRepository(session).list(event_type="integration.connected")

    [event] = events
    assert event.actor_id == admin.id
    assert event.organization_id == admin.organization_id
    assert event.payload["integration_id"] == created.json()["id"]
    assert event.payload["provider"] == "docusign"
    assert event.payload["connected_by"] == str(admin.id)
    assert "super-secret-value" not in json.dumps(event.payload)


async def test_integration_is_not_created_when_its_audit_event_fails(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = await _admin_headers(client)
    monkeypatch.setattr(
        integration_service, "emit_audit_event", AsyncMock(side_effect=RuntimeError("audit down"))
    )

    with pytest.raises(RuntimeError, match="audit down"):
        await client.post(
            "/api/integrations", json={"provider": "slack", "config": {}}, headers=headers
        )

    listed = await client.get("/api/integrations", headers=headers)
    assert listed.json() == []
