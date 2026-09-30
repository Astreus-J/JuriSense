"""#57/#58: Policy/PolicyVersion/Rule CRUD, draft-only rule mutation, and the publish
action's two invariants -- BR-POL-001 (rule immutability, enforced even bypassing the
API route) and BR-POL-002 (exactly one current version per policy)."""

import httpx

from app.policies.domain.errors import PublishedRuleImmutableError
from app.policies.infrastructure.repositories import RuleRepository
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


async def _create_policy(
    client: httpx.AsyncClient, headers: dict, name: str = "Vendor Policy"
) -> dict:
    response = await client.post("/api/policies", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_policy_creates_initial_draft_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-create@example.com")
    body = await _create_policy(client, headers)
    assert body["policy"]["status"] == "draft"
    assert body["initial_version"]["version_number"] == 1
    assert body["initial_version"]["status"] == "draft"
    assert body["initial_version"]["is_current"] is False


async def test_create_policy_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/policies", json={"name": "x"})
    assert response.status_code == 401


async def test_create_rule_on_draft_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-rule-create@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    rule = response.json()
    assert rule["rule_key"] == "SANC-001"
    assert rule["result_status"] == "BLOCK"
    assert rule["is_frozen"] is False
    assert "has(supplier)" in rule["compiled_presence_cel"]


async def test_create_rule_rejects_invalid_yaml_before_saving(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-rule-invalid@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": "rule: [unterminated"},
        headers=headers,
    )
    assert response.status_code == 422

    rules = (
        await client.get(
            f"/api/policies/{policy_id}/versions/{version_id}/rules", headers=headers
        )
    ).json()
    assert rules == []


async def test_create_rule_rejects_unknown_field(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-rule-unknown@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    bad_yaml = """
rule:
  id: BAD-001
  name: Bad
when:
  contract.not_a_real_field: true
result:
  status: BLOCK
severity: critical
approver_role: null
"""
    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": bad_yaml},
        headers=headers,
    )
    assert response.status_code == 422
    assert "not a recognized evaluation-context field" in response.json()["detail"]


async def test_duplicate_rule_key_in_same_version_is_conflict(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-rule-dup@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    first = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=headers,
    )
    second = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 409


async def test_update_rule_on_draft_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-rule-update@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    created = (
        await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": SANC_001_YAML},
            headers=headers,
        )
    ).json()

    updated_yaml = SANC_001_YAML.replace("critical", "high")
    response = await client.put(
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{created['id']}",
        json={"yaml": updated_yaml},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["severity"] == "high"


async def test_publish_freezes_rules_and_sets_current_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-publish@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=headers,
    )

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers
    )
    assert response.status_code == 200
    published = response.json()
    assert published["status"] == "published"
    assert published["is_current"] is True
    assert published["published_at"] is not None

    policy = (await client.get(f"/api/policies/{policy_id}", headers=headers)).json()
    assert policy["status"] == "published"

    rules = (
        await client.get(
            f"/api/policies/{policy_id}/versions/{version_id}/rules", headers=headers
        )
    ).json()
    assert rules[0]["is_frozen"] is True


async def test_publish_rejects_an_already_published_version(client: httpx.AsyncClient) -> None:
    headers = await register_org_and_login(client, "policy-publish-twice@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    await client.post(f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers)
    second = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers
    )
    assert second.status_code == 409


async def test_editing_a_rule_after_publish_is_rejected_at_the_api(
    client: httpx.AsyncClient,
) -> None:
    headers = await register_org_and_login(client, "policy-edit-after-publish@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    rule = (
        await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": SANC_001_YAML},
            headers=headers,
        )
    ).json()
    await client.post(f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers)

    response = await client.put(
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule['id']}",
        json={"yaml": SANC_001_YAML.replace("critical", "high")},
        headers=headers,
    )
    assert response.status_code == 409


async def test_frozen_rule_rejects_direct_mutation_bypassing_the_service(
    client: httpx.AsyncClient, db_session_factory
) -> None:
    """BR-POL-001, exercised at the domain layer directly: even a code path that never
    goes through `rule_service.update_rule`/the API route at all must still be refused.
    Loads the now-published, now-frozen `Rule` row in a brand-new session (never having
    gone through `rule_service`) and attempts a raw ORM mutation."""
    headers = await register_org_and_login(client, "policy-domain-guard@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    version_id = body["initial_version"]["id"]

    rule = (
        await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": SANC_001_YAML},
            headers=headers,
        )
    ).json()
    await client.post(f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers)

    import uuid as uuid_module

    async with db_session_factory() as session:
        loaded = await RuleRepository(session).get_by_id(uuid_module.UUID(rule["id"]))
        assert loaded.is_frozen is True
        try:
            loaded.severity = "low"
            raised = False
        except PublishedRuleImmutableError:
            raised = True
        assert raised, "Expected PublishedRuleImmutableError on direct mutation of a frozen Rule"


async def test_new_draft_version_copies_rules_and_publish_supersedes_current(
    client: httpx.AsyncClient,
) -> None:
    """BR-POL-001's copy-modify path + BR-POL-002: publishing version 2 must flip
    version 1's `is_current` to False."""
    headers = await register_org_and_login(client, "policy-new-draft@example.com")
    body = await _create_policy(client, headers)
    policy_id = body["policy"]["id"]
    v1_id = body["initial_version"]["id"]

    await client.post(
        f"/api/policies/{policy_id}/versions/{v1_id}/rules",
        json={"yaml": SANC_001_YAML},
        headers=headers,
    )
    await client.post(f"/api/policies/{policy_id}/versions/{v1_id}/publish", headers=headers)

    v2 = (
        await client.post(f"/api/policies/{policy_id}/versions", headers=headers)
    ).json()
    assert v2["version_number"] == 2
    assert v2["status"] == "draft"

    v2_rules = (
        await client.get(f"/api/policies/{policy_id}/versions/{v2['id']}/rules", headers=headers)
    ).json()
    assert len(v2_rules) == 1
    assert v2_rules[0]["rule_key"] == "SANC-001"
    assert v2_rules[0]["is_frozen"] is False  # fresh, unfrozen copy

    # Add FIN-003 to the new draft too, then publish it.
    await client.post(
        f"/api/policies/{policy_id}/versions/{v2['id']}/rules",
        json={"yaml": FIN_003_YAML},
        headers=headers,
    )
    await client.post(f"/api/policies/{policy_id}/versions/{v2['id']}/publish", headers=headers)

    v1_after = (
        await client.get(f"/api/policies/{policy_id}/versions/{v1_id}", headers=headers)
    ).json()
    v2_after = (
        await client.get(f"/api/policies/{policy_id}/versions/{v2['id']}", headers=headers)
    ).json()
    assert v1_after["is_current"] is False
    assert v2_after["is_current"] is True


async def test_policies_are_scoped_to_the_caller_organization(client: httpx.AsyncClient) -> None:
    headers_a = await register_org_and_login(client, "policy-org-a@example.com")
    headers_b = await register_org_and_login(client, "policy-org-b@example.com")
    body = await _create_policy(client, headers_a)

    response = await client.get(f"/api/policies/{body['policy']['id']}", headers=headers_b)
    assert response.status_code == 404
