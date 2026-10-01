"""Shared helpers for Approvals & Decisions tests: reuses the same hermetic
HTTP-mocking + org/supplier/contract bootstrapping fixtures Policies' own tests already
assembled (mirrors `tests/policies/conftest.py`'s re-export pattern exactly), plus a
helper for creating a second user with a specific role (an approver resolving their own
queue) and logging in as them.
"""

import httpx

from tests.contracts.conftest import (  # noqa: F401
    HIGH_CONFIDENCE_ENVELOPE,
    create_supplier,
    mock_openrouter,
    pdf_bytes_with_text,
)
from tests.suppliers.conftest import (  # noqa: F401
    ACTIVE_CNPJ_RESPONSE,
    mock_cnpj_registry,
    register_org_and_login,
    seed_sanctions_index,
)


async def create_user_and_login(
    client: httpx.AsyncClient,
    admin_headers: dict,
    *,
    email: str,
    role: str,
    password: str = "StrongPass1",
) -> dict:
    """Creates a second user with `role` inside the admin's organization (`POST
    /api/users`, admin-only) and logs in as them -- the "an approver resolves their own
    queue" setup every state-machine test needs."""
    created = await client.post(
        "/api/users",
        json={"full_name": "Test Approver", "email": email, "password": password, "role": role},
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
