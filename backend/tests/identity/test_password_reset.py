"""Password recovery: 1h single-use token, no enumeration, revokes sessions."""

import re

import httpx

from tests.conftest import CapturingEmailSender

REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
}


def _extract_token(sender: CapturingEmailSender) -> str:
    body = sender.messages[-1]["body"]
    return re.search(r"token=([\w~.-]+)", body).group(1)


async def _prepare(client: httpx.AsyncClient, sender: CapturingEmailSender) -> str:
    await client.post("/api/auth/register", json=REGISTRATION)
    await client.post("/api/auth/password/forgot", json={"email": REGISTRATION["email"]})
    return _extract_token(sender)


async def test_forgot_does_not_reveal_existence(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)

    existing = await client.post(
        "/api/auth/password/forgot", json={"email": REGISTRATION["email"]}
    )
    nonexistent = await client.post(
        "/api/auth/password/forgot", json={"email": "nobody@example.com"}
    )

    assert existing.status_code == nonexistent.status_code == 202
    assert existing.json() == nonexistent.json()


async def test_reset_changes_password_and_notifies(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    token = await _prepare(client, sent_emails)

    response = await client.post(
        "/api/auth/password/reset", json={"token": token, "new_password": "NewPass22"}
    )
    assert response.status_code == 200

    old_password = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    new_password = await client.post(
        "/api/auth/login", json={"email": REGISTRATION["email"], "password": "NewPass22"}
    )
    assert old_password.status_code == 401
    assert new_password.status_code == 200

    # Post-change notification
    assert "changed" in sent_emails.messages[-1]["subject"].lower()


async def test_reset_token_single_use(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    token = await _prepare(client, sent_emails)
    await client.post(
        "/api/auth/password/reset", json={"token": token, "new_password": "NewPass22"}
    )

    reuse = await client.post(
        "/api/auth/password/reset", json={"token": token, "new_password": "OtherPass33"}
    )
    assert reuse.status_code == 400


async def test_new_request_invalidates_previous_token(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    old_token = await _prepare(client, sent_emails)
    await client.post("/api/auth/password/forgot", json={"email": REGISTRATION["email"]})

    response = await client.post(
        "/api/auth/password/reset", json={"token": old_token, "new_password": "NewPass22"}
    )
    assert response.status_code == 400


async def test_reset_revokes_old_sessions(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    """MED-001: refresh tokens issued before the change stop being valid."""
    await client.post("/api/auth/register", json=REGISTRATION)
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    old_refresh = login.json()["refresh_token"]

    await client.post("/api/auth/password/forgot", json={"email": REGISTRATION["email"]})
    token = _extract_token(sent_emails)
    await client.post(
        "/api/auth/password/reset", json={"token": token, "new_password": "NewPass22"}
    )

    response = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 401


async def test_reset_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/password/reset",
        json={"token": "nonexistent-token", "new_password": "NewPass22"},
    )
    assert response.status_code == 400
