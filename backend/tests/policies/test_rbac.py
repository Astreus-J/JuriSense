"""RBAC 403 coverage for `Module.POLICIES`/`Module.COMPLIANCE_REVIEWS` routes (QA gap,
2026-09-30): every other bounded context's test suite has at least one
`test_viewer_role_cannot_*` case (e.g. `tests/suppliers/test_supplier_crud.py`), but
`tests/policies/` had zero, despite `app.policies.api.routes` gating every write on
`require_permission` exactly like every other context. Per `DEFAULT_ROLE_GRID`
(`app/identity/domain/rbac.py`), `viewer` has read-only access to both `policies` and
`compliance_reviews` -- every write below must be a clean 403, and reads must still
succeed, proving the dependency isn't over-blocking."""

import httpx

from tests.suppliers.conftest import register_org_and_login

SANC_001_YAML = """
rule:
  id: SANC-001
  name: Supplier on a Sanctions List
when:
  supplier.sanctions_hit: true
result:
  status: BLOCK
severity: critical
approver_role: null
"""


async def _create_policy(
    client: httpx.AsyncClient, headers: dict, name: str = "Vendor Policy"
) -> dict:
    response = await client.post("/api/policies", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _register_viewer(client: httpx.AsyncClient, admin_email: str, viewer_email: str) -> dict:
    admin_headers = await register_org_and_login(client, admin_email)
    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": viewer_email,
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login", json={"email": viewer_email, "password": "StrongPass1"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_viewer_role_cannot_create_policy(client: httpx.AsyncClient) -> None:
    viewer_headers = await _register_viewer(
        client, "admin-pol-rbac-1@example.com", "viewer-pol-rbac-1@example.com"
    )
    response = await client.post(
        "/api/policies", json={"name": "Should Fail"}, headers=viewer_headers
    )
    assert response.status_code == 403


async def test_viewer_role_cannot_create_rule(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "admin-pol-rbac-2@example.com")
    body = await _create_policy(client, admin_headers)
    policy_id, version_id = body["policy"]["id"], body["initial_version"]["id"]

    # The viewer must be a member of the SAME organization that owns the policy, so
    # invite them through `admin_headers` rather than registering a fresh org.
    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-pol-rbac-2@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "viewer-pol-rbac-2@example.com", "password": "StrongPass1"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_viewer_role_cannot_update_rule(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "admin-pol-rbac-3@example.com")
    body = await _create_policy(client, admin_headers)
    policy_id, version_id = body["policy"]["id"], body["initial_version"]["id"]
    rule_resp = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=admin_headers,
    )
    rule_id = rule_resp.json()["id"]

    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-pol-rbac-3@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "viewer-pol-rbac-3@example.com", "password": "StrongPass1"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.put(
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule_id}",
        json={"yaml": SANC_001_YAML},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_viewer_role_cannot_publish_version(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "admin-pol-rbac-4@example.com")
    body = await _create_policy(client, admin_headers)
    policy_id, version_id = body["policy"]["id"], body["initial_version"]["id"]

    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-pol-rbac-4@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "viewer-pol-rbac-4@example.com", "password": "StrongPass1"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=viewer_headers
    )
    assert response.status_code == 403


async def test_viewer_role_cannot_trigger_compliance_review(client: httpx.AsyncClient) -> None:
    viewer_headers = await _register_viewer(
        client, "admin-pol-rbac-5@example.com", "viewer-pol-rbac-5@example.com"
    )
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": "00000000-0000-0000-0000-000000000000"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_viewer_role_cannot_run_simulation(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "admin-pol-rbac-6@example.com")
    body = await _create_policy(client, admin_headers)
    policy_id, version_id = body["policy"]["id"], body["initial_version"]["id"]

    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-pol-rbac-6@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "viewer-pol-rbac-6@example.com", "password": "StrongPass1"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/simulate",
        json={"contract_version_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=viewer_headers,
    )
    assert response.status_code == 403


async def test_viewer_role_can_still_read_policies(client: httpx.AsyncClient) -> None:
    """The dependency must gate writes only -- read access (`_READ` in the grid) must
    keep working, or this would be an availability regression disguised as a security
    fix."""
    admin_headers = await register_org_and_login(client, "admin-pol-rbac-7@example.com")
    body = await _create_policy(client, admin_headers)
    policy_id = body["policy"]["id"]

    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-pol-rbac-7@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "viewer-pol-rbac-7@example.com", "password": "StrongPass1"},
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    list_response = await client.get("/api/policies", headers=viewer_headers)
    assert list_response.status_code == 200

    detail_response = await client.get(f"/api/policies/{policy_id}", headers=viewer_headers)
    assert detail_response.status_code == 200
