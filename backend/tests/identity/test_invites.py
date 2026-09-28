"""Invitations: admin invites, invitee sets a password, resending invalidates the previous one."""

import re

import httpx

from tests.conftest import CapturingEmailSender

REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
    "plan": "business",
}


def _token_from_last_email(sender: CapturingEmailSender) -> str:
    return re.search(r"token=([\w~.-]+)", sender.messages[-1]["body"]).group(1)


async def _admin_headers(client: httpx.AsyncClient, plan: str = "business") -> dict:
    await client.post("/api/auth/register", json={**REGISTRATION, "plan": plan})
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _invite(client: httpx.AsyncClient, headers: dict, **fields) -> httpx.Response:
    payload = {"email": "bruno@example.com", "role": "legal", **fields}
    return await client.post("/api/users/invites", json=payload, headers=headers)


async def test_full_invite_flow(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)

    invitation = await _invite(client, headers)
    assert invitation.status_code == 201
    assert invitation.json()["status"] == "pending"

    token = _token_from_last_email(sent_emails)
    acceptance = await client.post(
        "/api/users/accept-invite",
        json={"token": token, "password": "StrongPass2", "full_name": "Bruno Souza"},
    )
    assert acceptance.status_code == 201
    assert acceptance.json()["role"] == "legal"

    login = await client.post(
        "/api/auth/login", json={"email": "bruno@example.com", "password": "StrongPass2"}
    )
    assert login.status_code == 200

    me = await client.get("/api/auth/me", headers=headers)
    assert acceptance.json()["organization_id"] == me.json()["organization_id"]

    listing = await client.get("/api/users/invites", headers=headers)
    assert listing.json()[0]["status"] == "accepted"


async def test_invite_requires_admin(client: httpx.AsyncClient) -> None:
    not_logged_in = await client.post(
        "/api/users/invites", json={"email": "x@example.com", "role": "viewer"}
    )
    assert not_logged_in.status_code == 401


async def test_resend_invalidates_previous_invite(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)

    await _invite(client, headers)
    old_token = _token_from_last_email(sent_emails)
    await _invite(client, headers)  # resend

    old_acceptance = await client.post(
        "/api/users/accept-invite",
        json={"token": old_token, "password": "StrongPass2", "full_name": "Bruno"},
    )
    assert old_acceptance.status_code == 400


async def test_invite_token_single_use(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)
    await _invite(client, headers)
    token = _token_from_last_email(sent_emails)

    payload = {"token": token, "password": "StrongPass2", "full_name": "Bruno"}
    first = await client.post("/api/users/accept-invite", json=payload)
    second = await client.post("/api/users/accept-invite", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400


async def test_invite_respects_plan_limit(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    # Starter plan: 1 user (the admin) — the invite is already blocked at creation
    headers = await _admin_headers(client, plan="starter")

    invitation = await _invite(client, headers)
    assert invitation.status_code == 402


async def test_invite_for_already_registered_email(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    invitation = await _invite(client, headers, email=REGISTRATION["email"])
    assert invitation.status_code == 409
