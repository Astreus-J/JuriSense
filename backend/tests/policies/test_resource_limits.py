"""#180 (security finding POL-004): a per-organization resource-exhaustion backstop on
Policies/PolicyVersions/Rules -- no limit existed before, and unbounded rows are an
unbounded Rule-evaluation cost lever (every currently-published PolicyVersion's Rules are
pooled into every trigger_review/simulate call). Each limit is driven by `Settings`
(`max_policies_per_organization`/`max_policy_versions_per_policy`/
`max_rules_per_policy_version`), monkeypatched down to 1 here so the test doesn't need to
create 100+ real rows to prove the boundary.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.config import get_settings
from tests.approvals.conftest import create_user_and_login
from tests.policies.conftest import (  # noqa: F401
    create_supplier,
    mock_openrouter,
)
from tests.suppliers.conftest import register_org_and_login

TAX_ID_A = "00000000000191"
TAX_ID_B = "11222333000181"

FIN_003_YAML = """
rule:
  id: FIN-003
  name: High-Value Contract Requires Legal Approval
when:
  contract.value.brl: { gte: 250000 }
result:
  status: REVIEW
severity: medium
approver_role: legal
"""


async def test_policy_creation_is_refused_once_the_organization_limit_is_reached(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_policies_per_organization", 1)
    headers = await register_org_and_login(client, "policy-limit@example.com")

    first = await client.post("/api/policies", json={"name": "Policy A"}, headers=headers)
    assert first.status_code == 201, first.text

    second = await client.post("/api/policies", json={"name": "Policy B"}, headers=headers)
    assert second.status_code == 403, second.text
    assert "limit" in second.json()["detail"].lower()


async def test_policy_creation_is_scoped_per_organization_not_global(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_policies_per_organization", 1)
    a_headers = await register_org_and_login(client, "policy-limit-org-a@example.com")
    b_headers = await register_org_and_login(client, "policy-limit-org-b@example.com")

    a_created = await client.post("/api/policies", json={"name": "Policy A"}, headers=a_headers)
    assert a_created.status_code == 201, a_created.text
    # Org A is now at its limit, but Org B hasn't created anything yet.
    b_created = await client.post("/api/policies", json={"name": "Policy B"}, headers=b_headers)
    assert b_created.status_code == 201, b_created.text


async def test_draft_version_creation_is_refused_once_the_per_policy_limit_is_reached(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await register_org_and_login(client, "version-limit@example.com")
    created = (
        await client.post("/api/policies", json={"name": "Policy A"}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    # The Policy already has 1 version (its initial draft) -- the limit below is already met.
    monkeypatch.setattr(get_settings(), "max_policy_versions_per_policy", 1)

    response = await client.post(f"/api/policies/{policy_id}/versions", headers=headers)
    assert response.status_code == 403, response.text
    assert "limit" in response.json()["detail"].lower()


async def test_rule_creation_is_refused_once_the_per_version_limit_is_reached(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await register_org_and_login(client, "rule-limit@example.com")
    created = (
        await client.post("/api/policies", json={"name": "Policy A"}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]

    monkeypatch.setattr(get_settings(), "max_rules_per_policy_version", 1)
    first = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": FIN_003_YAML},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    other_rule_yaml = FIN_003_YAML.replace("FIN-003", "FIN-004")
    second = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": other_rule_yaml},
        headers=headers,
    )
    assert second.status_code == 403, second.text
    assert "limit" in second.json()["detail"].lower()


async def test_exception_grant_is_refused_once_the_per_rule_limit_is_reached(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Security review (2026-10-12): same POL-004 backstop, scoped per Rule -- nothing
    else bounded how many active `PolicyException` rows one Rule could accumulate."""
    admin_headers = await register_org_and_login(client, "exception-limit@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exception-limit-legal@example.com", role="legal"
    )
    created = (
        await client.post("/api/policies", json={"name": "Policy A"}, headers=admin_headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]
    rule = (
        await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": FIN_003_YAML},
            headers=admin_headers,
        )
    ).json()
    publish = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=admin_headers
    )
    assert publish.status_code == 200, publish.text

    supplier_a = await create_supplier(client, admin_headers, tax_id=TAX_ID_A)
    supplier_b = await create_supplier(client, admin_headers, tax_id=TAX_ID_B)
    exceptions_url = (
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule['id']}/exceptions"
    )
    valid_until = (datetime.now(UTC) + timedelta(days=30)).isoformat()

    monkeypatch.setattr(get_settings(), "max_active_exceptions_per_rule", 1)
    first = await client.post(
        exceptions_url,
        json={
            "supplier_id": supplier_a["id"],
            "justification": "First grant, within the limit.",
            "valid_until": valid_until,
        },
        headers=legal_headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        exceptions_url,
        json={
            "supplier_id": supplier_b["id"],
            "justification": "Second grant for a different target -- still the same rule.",
            "valid_until": valid_until,
        },
        headers=legal_headers,
    )
    assert second.status_code == 403, second.text
    assert "limit" in second.json()["detail"].lower()
