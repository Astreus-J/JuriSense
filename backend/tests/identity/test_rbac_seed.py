"""STORY-1.1.1: every role gets a sensible default permission grid automatically, seeded
as real `ModulePermission` rows the moment a `User` is created (ADR-012 — RBAC as data).
"""

import re
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.domain.constants import Module, Role
from app.identity.domain.rbac import DEFAULT_ROLE_GRID
from app.identity.infrastructure.models import ModulePermission, User
from tests.conftest import CapturingEmailSender

REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana-rbac@example.com",
    "password": "StrongPass1",
    "plan": "business",
}


async def _grid_for_user(db_session_factory: async_sessionmaker, user_id: uuid.UUID) -> dict:
    async with db_session_factory() as session:
        result = await session.execute(
            select(ModulePermission).where(ModulePermission.user_id == user_id)
        )
        return {row.module: row for row in result.scalars()}


def _assert_matches_default_grid(grid: dict, role: Role) -> None:
    expected = DEFAULT_ROLE_GRID[role]
    assert set(grid) == {module.value for module in Module}
    for module, permission in expected.items():
        row = grid[module.value]
        assert row.can_create == permission.can_create
        assert row.can_read == permission.can_read
        assert row.can_update == permission.can_update
        assert row.can_delete == permission.can_delete


def test_every_role_has_a_non_empty_default_grid_across_all_modules() -> None:
    assert set(DEFAULT_ROLE_GRID) == set(Role)
    for role, grid in DEFAULT_ROLE_GRID.items():
        assert set(grid) == set(Module), f"{role} is missing a module in its default grid"
        assert any(
            permission.can_create
            or permission.can_read
            or permission.can_update
            or permission.can_delete
            for permission in grid.values()
        ), f"{role} has an entirely empty default grid"


async def test_registered_admin_inherits_the_admin_default_grid_immediately(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)

    async with db_session_factory() as session:
        admin = (
            await session.execute(select(User).where(User.email == REGISTRATION["email"]))
        ).scalar_one()

    grid = await _grid_for_user(db_session_factory, admin.id)
    _assert_matches_default_grid(grid, Role.ADMIN)


async def test_admin_created_user_inherits_their_role_default_grid(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = await client.post(
        "/api/users",
        json={
            "full_name": "Pedro Procurement",
            "email": "pedro-rbac@example.com",
            "password": "StrongPass1",
            "role": "procurement",
        },
        headers=headers,
    )
    assert created.status_code == 201

    grid = await _grid_for_user(db_session_factory, uuid.UUID(created.json()["id"]))
    _assert_matches_default_grid(grid, Role.PROCUREMENT)


async def test_invited_user_inherits_their_role_default_grid_on_acceptance(
    client: httpx.AsyncClient,
    sent_emails: CapturingEmailSender,
    db_session_factory: async_sessionmaker,
) -> None:
    await client.post("/api/auth/register", json=REGISTRATION)
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    await client.post(
        "/api/users/invites",
        json={"email": "bruno-rbac@example.com", "role": "auditor"},
        headers=headers,
    )
    token = re.search(r"token=([\w~.-]+)", sent_emails.messages[-1]["body"]).group(1)

    acceptance = await client.post(
        "/api/users/accept-invite",
        json={"token": token, "password": "StrongPass2", "full_name": "Bruno Souza"},
    )
    assert acceptance.status_code == 201

    grid = await _grid_for_user(db_session_factory, uuid.UUID(acceptance.json()["id"]))
    _assert_matches_default_grid(grid, Role.AUDITOR)


async def test_role_change_reseeds_the_permission_grid(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Regression: PATCH /api/users/{id} with a new role used to leave the user's
    ModulePermission grid stale at their old role's defaults -- a demoted admin kept full
    CRUD everywhere indefinitely, since has_permission() only ever reads the persisted
    grid, never re-derives it from the user's current role."""
    await client.post("/api/auth/register", json=REGISTRATION)
    login = await client.post(
        "/api/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = await client.post(
        "/api/users",
        json={
            "full_name": "Priya Procurement",
            "email": "priya-rbac@example.com",
            "password": "StrongPass1",
            "role": "procurement",
        },
        headers=headers,
    )
    user_id = uuid.UUID(created.json()["id"])

    grid = await _grid_for_user(db_session_factory, user_id)
    _assert_matches_default_grid(grid, Role.PROCUREMENT)

    response = await client.patch(f"/api/users/{user_id}", json={"role": "viewer"}, headers=headers)
    assert response.status_code == 200

    grid = await _grid_for_user(db_session_factory, user_id)
    _assert_matches_default_grid(grid, Role.VIEWER)
