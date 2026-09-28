"""FEATURE-0.3: AuditEvent is emitted for the 5 Identity actions, and is append-only.

STORY-0.3.1 / STORY-0.3.2 / BR-EVD-003 / AUD-002.
"""

import re

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.models import AuditEvent
from app.evidence.infrastructure.repositories import AuditEventRepository
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


async def test_each_identity_action_emits_exactly_one_audit_event(
    client: httpx.AsyncClient,
    sent_emails: CapturingEmailSender,
    db_session_factory: async_sessionmaker,
) -> None:
    # organization.created + user.registered
    await client.post("/api/auth/register", json=REGISTRATION)
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # membership.invited
    await client.post(
        "/api/users/invites",
        json={"email": "bruno@example.com", "role": "legal"},
        headers=headers,
    )
    token = _token_from_last_email(sent_emails)

    # membership.accepted
    accept = await client.post(
        "/api/users/accept-invite",
        json={"token": token, "password": "StrongPass2", "full_name": "Bruno Souza"},
    )
    bruno_id = accept.json()["id"]

    # membership.revoked
    await client.delete(f"/api/users/{bruno_id}", headers=headers)

    async with db_session_factory() as session:
        repo = AuditEventRepository(session)
        for event_type in (
            "organization.created",
            "user.registered",
            "membership.invited",
            "membership.accepted",
            "membership.revoked",
        ):
            events = await repo.list(event_type=event_type)
            assert len(events) == 1, f"expected exactly one {event_type} event, got {len(events)}"


async def test_audit_event_repository_has_no_update_or_delete_path() -> None:
    """BR-EVD-003/AUD-002: no actor, including Admin, has any way to alter or remove
    a recorded AuditEvent — enforced by the repository simply exposing no such method.
    """
    exposed_methods = {name for name in dir(AuditEventRepository) if not name.startswith("_")}

    assert exposed_methods == {"add", "get", "list"}
    for forbidden in ("update", "edit", "delete", "remove", "patch"):
        assert forbidden not in exposed_methods


async def test_audit_event_persists_and_is_queryable(
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        repo = AuditEventRepository(session)
        repo.add(
            AuditEvent(
                event_type="organization.created",
                actor_id=None,
                organization_id=None,
                payload={"note": "direct repository test"},
            )
        )
        await session.commit()

        events = await repo.list(event_type="organization.created")
        assert len(events) == 1
        fetched = await repo.get(events[0].id)
        assert fetched is not None
        assert fetched.payload == {"note": "direct repository test"}
