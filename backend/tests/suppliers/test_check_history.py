"""STORY-2.9 / SUP-005: immutable SupplierCheck history, ordered most-recent-first, RBAC-
gated for read. Also BR-SUP-003's approval guard: both the success and rejection paths.
"""

import httpx

from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login

TAX_ID = "00000000000191"


async def _create_and_approve_ready_supplier(
    client: httpx.AsyncClient,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_supplier_checks_inline,
    email: str,
) -> tuple[dict, dict]:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index()
    headers = await register_org_and_login(client, email)
    created = (
        await client.post(
            "/api/suppliers",
            json={"legal_name": "Banco do Brasil SA", "tax_id": TAX_ID, "jurisdiction": "BR"},
            headers=headers,
        )
    ).json()
    return created, headers


async def test_check_history_is_ordered_most_recent_first(
    client: httpx.AsyncClient, mock_cnpj_registry, seed_sanctions_index, run_supplier_checks_inline
) -> None:
    created, headers = await _create_and_approve_ready_supplier(
        client,
        mock_cnpj_registry,
        seed_sanctions_index,
        run_supplier_checks_inline,
        "history-order@example.com",
    )
    await client.post(f"/api/suppliers/{created['id']}/recheck", headers=headers)
    await client.post(f"/api/suppliers/{created['id']}/recheck", headers=headers)

    history = (await client.get(f"/api/suppliers/{created['id']}/checks", headers=headers)).json()

    assert len(history) == 3
    started_ats = [c["started_at"] for c in history]
    assert started_ats == sorted(started_ats, reverse=True)


async def test_check_history_scoped_to_own_organization(
    client: httpx.AsyncClient, mock_cnpj_registry, seed_sanctions_index, run_supplier_checks_inline
) -> None:
    created, headers_a = await _create_and_approve_ready_supplier(
        client,
        mock_cnpj_registry,
        seed_sanctions_index,
        run_supplier_checks_inline,
        "history-a@example.com",
    )
    headers_b = await register_org_and_login(client, "history-b@example.com")

    other_org_read = await client.get(f"/api/suppliers/{created['id']}/checks", headers=headers_b)
    assert other_org_read.status_code == 404


async def test_viewer_can_read_but_not_trigger_recheck(
    client: httpx.AsyncClient, mock_cnpj_registry, seed_sanctions_index, run_supplier_checks_inline
) -> None:
    created, admin_headers = await _create_and_approve_ready_supplier(
        client,
        mock_cnpj_registry,
        seed_sanctions_index,
        run_supplier_checks_inline,
        "history-viewer@example.com",
    )
    await client.post(
        "/api/users",
        json={
            "full_name": "Viewer",
            "email": "viewer-history@example.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    login = await client.post(
        "/api/auth/login", json={"email": "viewer-history@example.com", "password": "StrongPass1"}
    )
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    read = await client.get(f"/api/suppliers/{created['id']}/checks", headers=viewer_headers)
    assert read.status_code == 200

    recheck = await client.post(f"/api/suppliers/{created['id']}/recheck", headers=viewer_headers)
    assert recheck.status_code == 403


async def test_br_sup_003_approval_succeeds_with_completed_clean_check(
    client: httpx.AsyncClient, mock_cnpj_registry, seed_sanctions_index, run_supplier_checks_inline
) -> None:
    created, headers = await _create_and_approve_ready_supplier(
        client,
        mock_cnpj_registry,
        seed_sanctions_index,
        run_supplier_checks_inline,
        "br-sup-003-ok@example.com",
    )

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "approved"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


async def test_br_sup_003_approval_rejected_without_any_check(client: httpx.AsyncClient) -> None:
    """A Supplier with no SupplierCheck at all (enqueue stubbed to a no-op by the default
    autouse fixture, so no check ever runs here) cannot be approved."""
    headers = await register_org_and_login(client, "br-sup-003-none@example.com")
    created = (
        await client.post(
            "/api/suppliers",
            json={"legal_name": "Acme", "tax_id": "44444444000144", "jurisdiction": "BR"},
            headers=headers,
        )
    ).json()

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "approved"}, headers=headers
    )

    assert response.status_code == 409


async def test_can_move_to_blocked_without_a_completed_check(client: httpx.AsyncClient) -> None:
    """BR-SUP-003 only gates the `approved` transition — blocking/deactivating a supplier
    (e.g. on external knowledge outside the platform) is not restricted the same way."""
    headers = await register_org_and_login(client, "block-no-check@example.com")
    created = (
        await client.post(
            "/api/suppliers",
            json={"legal_name": "Acme", "tax_id": "55555555000155", "jurisdiction": "BR"},
            headers=headers,
        )
    ).json()

    response = await client.patch(
        f"/api/suppliers/{created['id']}/status", json={"status": "blocked"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
