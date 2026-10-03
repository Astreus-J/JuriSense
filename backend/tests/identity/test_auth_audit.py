"""FEATURE-7.2 / STORY-7.2.1: AuditEvents for login success, login failure (including the
inactive-account refusal), and self-service password reset [AUD-001].

The failed-login payload must never carry the plaintext address or the password, and the
HTTP response must stay exactly what it was before the event was added.
"""

import json
import re
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.application import password_service
from app.identity.infrastructure.repositories import UserRepository
from tests.conftest import CapturingEmailSender

EMAIL = "ana@example.com"
PASSWORD = "StrongPass1"
REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": EMAIL,
    "password": PASSWORD,
}
# The exact body the failed-login response had before user.login_failed was added.
INVALID_CREDENTIALS_BODY = b'{"detail":"Invalid credentials"}'


async def _login(
    client: httpx.AsyncClient, email: str = EMAIL, password: str = PASSWORD
) -> httpx.Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def _user(db_session_factory: async_sessionmaker, email: str):
    async with db_session_factory() as session:
        return await UserRepository(session).get_by_email(email)


async def _events(db_session_factory: async_sessionmaker, event_type: str) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(event_type=event_type)


async def test_successful_login_emits_user_login_succeeded(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)
    user = await _user(db_session_factory, EMAIL)

    response = await _login(client)
    assert response.status_code == 200

    [event] = await _events(db_session_factory, "user.login_succeeded")
    assert event.actor_id == user.id
    assert event.organization_id == user.organization_id
    assert set(event.payload) == {"user_id", "occurred_at"}
    assert event.payload["user_id"] == str(user.id)


async def test_failed_login_emits_user_login_failed_and_response_is_unchanged(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)
    user = await _user(db_session_factory, EMAIL)

    wrong_password = await _login(client, password="WrongPass1")
    unknown_email = await _login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.content == unknown_email.content == INVALID_CREDENTIALS_BODY

    events = await _events(db_session_factory, "user.login_failed")
    assert len(events) == 2

    [known] = [e for e in events if e.payload["user_id_attempted"] == str(user.id)]
    assert known.actor_id is None
    assert known.organization_id == user.organization_id
    assert known.payload["reason"] == "invalid_credentials"

    [unknown] = [e for e in events if e.payload["user_id_attempted"] is None]
    assert unknown.organization_id is None
    assert unknown.payload["reason"] == "invalid_credentials"

    # Data minimization: neither the attempted address nor any hash of it is stored.
    serialized = json.dumps([event.payload for event in events])
    for forbidden in (EMAIL, "nobody@example.com", PASSWORD, "WrongPass1"):
        assert forbidden not in serialized
    assert "email" not in serialized


async def test_refused_inactive_account_emits_user_login_failed_with_reason(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json={**REGISTRATION, "plan": "business"})
    admin_login = await _login(client)
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    created = await client.post(
        "/api/users",
        json={
            "full_name": "Bruno Souza",
            "email": "bruno@example.com",
            "password": PASSWORD,
            "role": "legal",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    bruno_id = created.json()["id"]
    deactivated = await client.patch(
        f"/api/users/{bruno_id}", json={"status": "inactive"}, headers=admin_headers
    )
    assert deactivated.status_code == 200, deactivated.text

    refused = await _login(client, email="bruno@example.com")
    assert refused.status_code == 401
    assert refused.content == INVALID_CREDENTIALS_BODY

    [event] = [
        e
        for e in await _events(db_session_factory, "user.login_failed")
        if e.payload["user_id_attempted"] == bruno_id
    ]
    assert event.payload["reason"] == "user_inactive"
    assert event.organization_id == (await _user(db_session_factory, EMAIL)).organization_id


async def test_password_reset_emits_user_password_reset(
    client: httpx.AsyncClient,
    sent_emails: CapturingEmailSender,
    db_session_factory: async_sessionmaker,
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)
    user = await _user(db_session_factory, EMAIL)
    await client.post("/api/auth/password/forgot", json={"email": EMAIL})
    token = re.search(r"token=([\w~.-]+)", sent_emails.messages[-1]["body"]).group(1)

    response = await client.post(
        "/api/auth/password/reset", json={"token": token, "new_password": "NewPass22"}
    )
    assert response.status_code == 200

    [event] = await _events(db_session_factory, "user.password_reset")
    assert event.actor_id == user.id
    assert event.organization_id == user.organization_id
    assert event.payload["user_id"] == str(user.id)
    assert event.payload["initiated_via"] == "self_service"


async def test_password_reset_is_atomic_with_its_audit_event(
    client: httpx.AsyncClient,
    sent_emails: CapturingEmailSender,
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the audit write fails, the password must not change: the event and the change
    share one transaction."""
    await client.post("/api/auth/register", json=REGISTRATION)
    await client.post("/api/auth/password/forgot", json={"email": EMAIL})
    token = re.search(r"token=([\w~.-]+)", sent_emails.messages[-1]["body"]).group(1)
    monkeypatch.setattr(
        password_service, "emit_audit_event", AsyncMock(side_effect=RuntimeError("audit down"))
    )

    with pytest.raises(RuntimeError, match="audit down"):
        await client.post(
            "/api/auth/password/reset", json={"token": token, "new_password": "NewPass22"}
        )

    assert (await _login(client)).status_code == 200
    assert await _events(db_session_factory, "user.password_reset") == []
