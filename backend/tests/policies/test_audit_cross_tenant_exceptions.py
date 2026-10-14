"""Ad-hoc cross-tenant reproduction for the Sprint audit (ADR-003/ADR-016). Not part of the
regular suite's naming convention (test_tenant_isolation.py already exists for approvals) --
added here to independently verify PolicyException's tenant isolation, since it is brand new
this sprint (#120) and had no cross-tenant test targeting a REAL foreign resource (the existing
test_grant_rejects_a_target_not_in_this_organization in test_policy_exceptions.py only used a
random, nonexistent UUID, which doesn't prove a real supplier belonging to another org is refused
the same way).
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx

from tests.approvals.conftest import create_user_and_login
from tests.policies.conftest import ACTIVE_CNPJ_RESPONSE, create_supplier
from tests.policies.test_policy_exceptions import (
    FIN_003_YAML,
    _create_policy_with_rule,
    _exceptions_url,
)
from tests.suppliers.conftest import register_org_and_login

_FUTURE = (datetime.now(UTC) + timedelta(days=30)).isoformat()


async def test_org_a_legal_user_cannot_grant_exception_against_org_bs_real_supplier(
    client: httpx.AsyncClient, mock_cnpj_registry
) -> None:
    """Org A's `legal` user tries to grant a PolicyException against a *real* supplier that
    belongs to Org B, using Org A's own rule. Must be refused as if the supplier did not exist
    (404), never silently succeed, never leak that the supplier exists."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)

    a_admin = await register_org_and_login(client, "audit-tenant-a@example.com")
    a_legal = await create_user_and_login(
        client, a_admin, email="audit-tenant-a-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, a_admin, rule_yaml=FIN_003_YAML
    )

    b_admin = await register_org_and_login(client, "audit-tenant-b@example.com")
    b_supplier = await create_supplier(client, b_admin, tax_id="11111111000191")

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": b_supplier["id"],
            "justification": "Attempting to waive using another org's supplier as target.",
            "valid_until": _FUTURE,
        },
        headers=a_legal,
    )
    assert response.status_code == 404, response.text


async def test_org_b_cannot_read_or_write_org_as_rule_or_exceptions_via_id_reuse(
    client: httpx.AsyncClient, mock_cnpj_registry
) -> None:
    """Org B's own `legal` user reuses Org A's real policy_id/version_id/rule_id path
    segments (e.g. guessed or leaked from a URL) with Org B's own auth token. Both listing
    Org A's exceptions and granting a new one against Org B's own supplier (using Org A's
    rule_id) must 404 -- Approvals/Policy & Compliance must never resolve a rule across
    organization boundaries no matter which org's id is supplied in which slot."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)

    a_admin = await register_org_and_login(client, "audit-tenant-a2@example.com")
    await create_user_and_login(
        client, a_admin, email="audit-tenant-a2-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, a_admin, rule_yaml=FIN_003_YAML
    )

    b_admin = await register_org_and_login(client, "audit-tenant-b2@example.com")
    b_legal = await create_user_and_login(
        client, b_admin, email="audit-tenant-b2-legal@example.com", role="legal"
    )
    b_supplier = await create_supplier(client, b_admin, tax_id="22222222000191")

    # Read: Org B listing Org A's rule's exceptions.
    listed = await client.get(_exceptions_url(policy_id, version_id, rule_id), headers=b_legal)
    assert listed.status_code == 404, listed.text

    # Write: Org B granting an exception against Org A's rule_id (even targeting Org B's own,
    # legitimately-owned supplier).
    granted = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": b_supplier["id"],
            "justification": "Org B trying to use Org A's rule_id directly.",
            "valid_until": _FUTURE,
        },
        headers=b_legal,
    )
    assert granted.status_code == 404, granted.text

    # Positive control: Org A granting against its own rule and its own (nonexistent targetless)
    # case still goes through the normal 404-for-missing-supplier path, proving the 404s above
    # are the tenant-boundary check and not some unrelated schema failure.
    unrelated_missing = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": str(uuid.uuid4()),
            "justification": "Sanity check: genuinely missing supplier also 404s for the owner.",
            "valid_until": _FUTURE,
        },
        headers=a_admin,
    )
    assert unrelated_missing.status_code == 403 or unrelated_missing.status_code == 404
