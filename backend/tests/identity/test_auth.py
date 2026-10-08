import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.infrastructure.models import AccessLog, Organization

REGISTRATION = {
    "organization_name": "Example Corp",
    "full_name": "Ana Silva",
    "email": "ana@example.com",
    "password": "StrongPass1",
}


async def _register(client: httpx.AsyncClient, **fields: str) -> httpx.Response:
    return await client.post("/api/auth/register", json={**REGISTRATION, **fields})


async def _login(
    client: httpx.AsyncClient, email: str = "ana@example.com", password: str = "StrongPass1"
) -> httpx.Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


# ---- Registration ----


async def test_register_creates_org_and_admin(client: httpx.AsyncClient) -> None:
    response = await _register(client)

    assert response.status_code == 202
    assert "password" not in response.text and "password_hash" not in response.text

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {(await _login(client)).json()['access_token']}"},
    )
    assert me.json()["email"] == "ana@example.com"
    assert me.json()["role"] == "admin"
    assert me.json()["is_active"] is True


async def test_register_duplicate_email_no_enumeration(client: httpx.AsyncClient) -> None:
    """MED-002: identical response whether or not the email exists."""
    first = await _register(client)
    second = await _register(client, organization_name="Another Corp")

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


async def test_register_email_normalized(client: httpx.AsyncClient) -> None:
    await _register(client, email="ANA@EXAMPLE.COM")

    response = await _login(client, email="ana@example.com")
    assert response.status_code == 200


async def test_register_weak_password(client: httpx.AsyncClient) -> None:
    response = await _register(client, password="short")

    assert response.status_code == 422
    assert "security policy" in response.json()["detail"]


async def test_register_enterprise_plan_persists_unlimited_limits(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Regression test (bug found 2026-10-08): `Organization`'s four plan-limit columns
    previously had a Python-side `mapped_column(default=...)`, which SQLAlchemy silently
    substitutes for an explicitly-set `None` at flush time -- so every Enterprise
    organization got Starter's numeric limits instead of the unlimited (`None`) sentinel
    `PLAN_LIMITS[Plan.ENTERPRISE]` actually specifies. Asserts directly against the
    persisted row, not just the API response, since `/auth/me` doesn't surface these fields."""
    await _register(client, email="enterprise@example.com", plan="enterprise")

    async with db_session_factory() as session:
        organization = (
            await session.execute(
                select(Organization).where(Organization.name == "Example Corp")
            )
        ).scalar_one()

    assert organization.plan == "enterprise"
    assert organization.user_limit is None
    assert organization.supplier_limit is None
    assert organization.storage_limit_gb is None
    assert organization.ai_execution_limit is None


# ---- Login ----


async def test_login_returns_tokens(client: httpx.AsyncClient) -> None:
    await _register(client)
    response = await _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_login_wrong_password_and_nonexistent_email_same_response(
    client: httpx.AsyncClient,
) -> None:
    await _register(client)
    wrong_password = await _login(client, password="WrongPass1")
    nonexistent_email = await _login(client, email="nobody@example.com")

    assert wrong_password.status_code == nonexistent_email.status_code == 401
    assert wrong_password.json() == nonexistent_email.json()


async def test_login_locks_after_5_failures(client: httpx.AsyncClient) -> None:
    await _register(client)
    for _ in range(5):
        response = await _login(client, password="WrongPass1")
        assert response.status_code == 401

    # Even with the correct password, the account is locked
    response = await _login(client)
    assert response.status_code == 429
    assert "Retry-After" in response.headers


# ---- Access log ----


async def test_login_records_access_log(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await _register(client)
    await _login(client)
    await _login(client, password="WrongPass1")

    async with db_session_factory() as session:
        total = await session.scalar(select(func.count(AccessLog.id)))
        successes = await session.scalar(
            select(func.count(AccessLog.id)).where(AccessLog.successful.is_(True))
        )
    assert total == 2
    assert successes == 1


# ---- Tokens: me, refresh, logout ----


async def _tokens(client: httpx.AsyncClient) -> dict[str, str]:
    await _register(client)
    return (await _login(client)).json()


async def test_me_requires_valid_token(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    no_token = await client.get("/api/auth/me")
    invalid_token = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    valid = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert no_token.status_code == 401
    assert invalid_token.status_code == 401
    assert valid.status_code == 200
    assert valid.json()["email"] == "ana@example.com"


async def test_refresh_token_does_not_work_as_access(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert response.status_code == 401


async def test_refresh_rotates_and_invalidates_previous(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    first = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != tokens["refresh_token"]

    # Reusing the already-consumed refresh token is rejected
    reuse = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401


async def test_logout_revokes_access_and_refresh(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=auth
    )
    assert response.status_code == 204

    me = await client.get("/api/auth/me", headers=auth)
    assert me.status_code == 401

    refresh = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401
