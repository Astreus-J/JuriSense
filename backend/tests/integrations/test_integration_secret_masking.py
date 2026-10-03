"""Security review H1 (2026-10-03): connector credentials in `Integration.config` must not be
returned in plaintext to any reader, including the AUDITOR and SECURITY roles that hold the
`read` permission. Non-credential values stay visible so the record remains useful."""

import httpx

from tests.integrations.test_integration_crud import _admin_headers, _user_headers_with_role

CONFIG = {
    "api_key": "sk-live-123",
    "base_url": "https://api.example.com",
    "webhook": {"signing_secret": "whsec-456", "path": "/hooks/docusign"},
    "clientCredentials": {"clientId": "public-id", "clientSecret": "very-secret"},
    "scopes": ["read", "write"],
}


def _assert_masked(config: dict) -> None:
    assert config["api_key"] == "********"
    assert config["webhook"]["signing_secret"] == "********"
    # A credential-named key masks its whole subtree, not just the leaves inside it.
    assert config["clientCredentials"] == "********"
    # Non-credential values are kept as they were stored.
    assert config["base_url"] == "https://api.example.com"
    assert config["webhook"]["path"] == "/hooks/docusign"
    assert config["scopes"] == ["read", "write"]
    serialized = str(config)
    for secret in ("sk-live-123", "whsec-456", "very-secret", "public-id"):
        assert secret not in serialized


async def test_create_response_masks_credentials(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client, "admin-h1-create@example.com")

    created = await client.post(
        "/api/integrations", json={"provider": "docusign", "config": CONFIG}, headers=headers
    )

    assert created.status_code == 201
    _assert_masked(created.json()["config"])


async def test_get_and_list_mask_credentials_for_security_role(client: httpx.AsyncClient) -> None:
    admin_headers = await _admin_headers(client, "admin-h1-read@example.com")
    created = await client.post(
        "/api/integrations", json={"provider": "docusign", "config": CONFIG}, headers=admin_headers
    )
    security_headers = await _user_headers_with_role(
        client, admin_headers, "security-h1@example.com", "security"
    )

    fetched = await client.get(
        f"/api/integrations/{created.json()['id']}", headers=security_headers
    )
    listed = await client.get("/api/integrations", headers=security_headers)

    assert fetched.status_code == 200
    _assert_masked(fetched.json()["config"])
    assert listed.status_code == 200
    [item] = listed.json()
    _assert_masked(item["config"])


async def test_config_without_credentials_is_returned_unchanged(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client, "admin-h1-plain@example.com")

    created = await client.post(
        "/api/integrations",
        json={"provider": "slack", "config": {"channel": "#legal", "retries": 3}},
        headers=headers,
    )

    assert created.json()["config"] == {"channel": "#legal", "retries": 3}
