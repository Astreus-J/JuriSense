"""Security audit (2026-10-12): `rate_limit_by_ip` (#112) shipped for the public
verification route but was never applied to Identity's own unauthenticated endpoints
(register/login/forgot-password/reset-password/accept-invite), each of which also does a
deliberately slow Argon2id hash per call (register, reset) or a DB write with no other
throttle -- a cheap per-IP CPU-exhaustion/spam lever with no backstop. `login` keeps its
existing per-EMAIL lockout independently; this is a per-IP budget shared across all five
routes (`key_prefix="identity_public"`), so one attacker IP can't bypass it by varying the
target email.
"""

import httpx

from app.core.config import get_settings
from tests.suppliers.conftest import register_org_and_login


async def test_register_is_rate_limited_per_ip_across_distinct_emails(
    client: httpx.AsyncClient,
) -> None:
    budget = get_settings().identity_rate_limit_max_requests

    for i in range(budget):
        response = await client.post(
            "/api/auth/register",
            json={
                "organization_name": f"Org {i}",
                "full_name": "Admin",
                "email": f"rate-limit-register-{i}@example.com",
                "password": "StrongPass1",
                "plan": "business",
            },
        )
        assert response.status_code == 202, response.text

    limited = await client.post(
        "/api/auth/register",
        json={
            "organization_name": "One Too Many",
            "full_name": "Admin",
            "email": "rate-limit-register-overflow@example.com",
            "password": "StrongPass1",
            "plan": "business",
        },
    )
    assert limited.status_code == 429, limited.text
    assert int(limited.headers["retry-after"]) > 0


async def test_login_shares_the_same_per_ip_budget_as_register(client: httpx.AsyncClient) -> None:
    """The budget is shared across every Identity public route (`key_prefix=
    "identity_public"`) -- registering up to the limit must also lock out a subsequent
    login attempt from the same (test) IP, proving the two routes aren't each silently
    getting their own separate budget."""
    headers = await register_org_and_login(client, "rate-limit-shared-budget@example.com")
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text

    budget = get_settings().identity_rate_limit_max_requests
    # register_org_and_login already spent 2 hits (register + login).
    for i in range(budget - 2):
        response = await client.post(
            "/api/auth/register",
            json={
                "organization_name": f"Shared Budget Org {i}",
                "full_name": "Admin",
                "email": f"rate-limit-shared-budget-filler-{i}@example.com",
                "password": "StrongPass1",
                "plan": "business",
            },
        )
        assert response.status_code == 202, response.text

    limited = await client.post(
        "/api/auth/login",
        json={"email": "rate-limit-shared-budget@example.com", "password": "StrongPass1"},
    )
    assert limited.status_code == 429, limited.text
