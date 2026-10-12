"""#120 (STORY-4.4.2): `PolicyException` -- an approver-signed, time-boxed waiver of one
REVIEW-tier rule for one Supplier or ContractVersion, and its wiring into
`evaluation_service`/`compliance_review_service` as a new `EXEMPTED` RuleOutcome.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx

from app.policies.infrastructure.models import PolicyException
from app.policies.infrastructure.repositories import PolicyExceptionRepository
from tests.approvals.conftest import create_user_and_login
from tests.policies.conftest import ACTIVE_CNPJ_RESPONSE, create_supplier, pdf_bytes_with_text
from tests.suppliers.conftest import register_org_and_login

TAX_ID = "00000000000191"

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

EVIDENCE_ENVELOPE = {
    "fields": {
        "value": {
            "amount": {
                "value": 300000,
                "confidence": 0.95,
                "provenance": {
                    "document_id": "doc-1",
                    "page": 1,
                    "text_span": {"start": 0, "end": 5},
                },
            },
            "currency": {
                "value": "BRL",
                "confidence": 0.95,
                "provenance": {
                    "document_id": "doc-1",
                    "page": 1,
                    "text_span": {"start": 5, "end": 8},
                },
            },
        },
    },
    "clauses": [],
}

_FUTURE = (datetime.now(UTC) + timedelta(days=30)).isoformat()
_PAST_ISO = (datetime.now(UTC) - timedelta(days=1)).isoformat()


async def _create_policy_with_rule(
    client: httpx.AsyncClient, headers: dict, *, rule_yaml: str
) -> tuple[str, str, str]:
    created = (
        await client.post("/api/policies", json={"name": "Vendor Policy"}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]
    rule = (
        await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": rule_yaml},
            headers=headers,
        )
    ).json()
    publish = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers
    )
    assert publish.status_code == 200, publish.text
    return policy_id, version_id, rule["id"]


async def _upload_contract(client: httpx.AsyncClient, headers: dict, supplier_id: str) -> str:
    upload = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier_id, "title": "High-Value MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    return upload["id"]


def _exceptions_url(policy_id: str, version_id: str, rule_id: str) -> str:
    return f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule_id}/exceptions"


async def test_legal_approver_grants_exception_for_their_own_waived_rule(
    client: httpx.AsyncClient, mock_openrouter, mock_cnpj_registry, run_contract_extraction_inline
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, "exc-grant@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-legal@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "contract_version_id": contract_version_id,
            "justification": "Renewal of an already-reviewed MSA, legal signed off out of band.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rule_id"] == rule_id
    assert body["contract_version_id"] == contract_version_id
    assert body["supplier_id"] is None
    assert body["approver_role"] == "legal"

    listed = await client.get(
        _exceptions_url(policy_id, version_id, rule_id), headers=admin_headers
    )
    assert listed.status_code == 200, listed.text
    assert [e["id"] for e in listed.json()] == [body["id"]]


async def test_grant_rejects_actor_without_the_waived_rules_approver_role(
    client: httpx.AsyncClient,
) -> None:
    """The admin role has `update` permission on Policies (passes `CanUpdatePolicies`),
    but is not `legal` -- `exception_service.grant_exception`'s own role-match check,
    not the route's permission gate, must be what refuses this."""
    admin_headers = await register_org_and_login(client, "exc-wrong-role@example.com")
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": supplier["id"],
            "justification": "Admin trying to self-approve.",
            "valid_until": _FUTURE,
        },
        headers=admin_headers,
    )
    assert response.status_code == 403, response.text


async def test_grant_rejects_a_block_tier_rule_with_no_approver_role(
    client: httpx.AsyncClient,
) -> None:
    admin_headers = await register_org_and_login(client, "exc-block-tier@example.com")
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=SANC_001_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": supplier["id"],
            "justification": "Trying to waive a BLOCK-tier rule.",
            "valid_until": _FUTURE,
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


async def test_grant_rejects_both_supplier_and_contract_version_given(
    client: httpx.AsyncClient,
) -> None:
    admin_headers = await register_org_and_login(client, "exc-both-targets@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-both-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": supplier["id"],
            "contract_version_id": str(uuid.uuid4()),
            "justification": "Both targets given.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert response.status_code == 422, response.text


async def test_grant_rejects_neither_target_given(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "exc-no-target@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-no-target-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={"justification": "No target given.", "valid_until": _FUTURE},
        headers=legal_headers,
    )
    assert response.status_code == 422, response.text


async def test_grant_rejects_empty_justification(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "exc-empty-justification@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-empty-justification-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={"supplier_id": supplier["id"], "justification": "   ", "valid_until": _FUTURE},
        headers=legal_headers,
    )
    assert response.status_code == 422, response.text


async def test_grant_rejects_a_valid_until_already_in_the_past(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "exc-past-valid-until@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-past-valid-until-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": supplier["id"],
            "justification": "Already expired at creation.",
            "valid_until": _PAST_ISO,
        },
        headers=legal_headers,
    )
    assert response.status_code == 422, response.text


async def test_grant_rejects_a_target_not_in_this_organization(client: httpx.AsyncClient) -> None:
    admin_headers = await register_org_and_login(client, "exc-foreign-target@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-foreign-target-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )

    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": str(uuid.uuid4()),
            "justification": "Nonexistent supplier.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert response.status_code == 404, response.text


async def test_trigger_review_exempts_a_rule_with_an_active_exception_for_its_target(
    client: httpx.AsyncClient, mock_openrouter, mock_cnpj_registry, run_contract_extraction_inline
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, "exc-exempt-flow@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-exempt-flow-legal@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])

    grant = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "contract_version_id": contract_version_id,
            "justification": "Renewal of an already-reviewed MSA.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert grant.status_code == 201, grant.text
    exception_id = grant.json()["id"]

    review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=admin_headers,
    )
    assert review.status_code == 201, review.text
    body = review.json()
    # FIN-003 would otherwise fire REVIEW (contract.value.brl=300000 >= 250000); exempted
    # instead, so the whole review's aggregate status is APPROVE, not REVIEW.
    assert body["status"] == "APPROVE"

    detail = await client.get(f"/api/compliance/reviews/{body['id']}", headers=admin_headers)
    evaluations = {e["rule_key"]: e for e in detail.json()["rule_evaluations"]}
    assert evaluations["FIN-003"]["outcome"] == "EXEMPTED"
    assert evaluations["FIN-003"]["exception_id"] == exception_id
    # An EXEMPTED outcome is not a finding -- no Risk row for it (#125's Risk-provenance
    # design decision: only REVIEW/BLOCK outcomes produce one).
    assert detail.json()["risks"] == []


async def test_trigger_review_does_not_exempt_the_same_rule_for_a_different_contract_version(
    client: httpx.AsyncClient, mock_openrouter, mock_cnpj_registry, run_contract_extraction_inline
) -> None:
    """An exception is scoped to the exact target it names -- a second, unrelated
    ContractVersion triggering the same rule must still get a real REVIEW outcome."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, "exc-scoped-flow@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-scoped-flow-legal@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    exempted_contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    other_contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])

    grant = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "contract_version_id": exempted_contract_version_id,
            "justification": "Scoped to one specific contract version only.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert grant.status_code == 201, grant.text

    review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": other_contract_version_id},
        headers=admin_headers,
    )
    assert review.status_code == 201, review.text
    assert review.json()["status"] == "REVIEW"


async def test_grant_accepts_a_naive_valid_until_as_utc(client: httpx.AsyncClient) -> None:
    """Code review (2026-10-12): Pydantic v2 parses a `valid_until` with no UTC offset
    into a naive `datetime` -- comparing that directly against `datetime.now(UTC)`
    previously raised an unhandled `TypeError` instead of a clean response. A bare
    timestamp is treated as already UTC, this codebase's existing convention for every
    other `DateTime(timezone=True)` column."""
    admin_headers = await register_org_and_login(client, "exc-naive-datetime@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-naive-datetime-legal@example.com", role="legal"
    )
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)

    future_naive = (datetime.now(UTC) + timedelta(days=30)).replace(tzinfo=None).isoformat()
    response = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "supplier_id": supplier["id"],
            "justification": "Naive datetime, no UTC offset.",
            "valid_until": future_naive,
        },
        headers=legal_headers,
    )
    assert response.status_code == 201, response.text


async def test_most_recently_granted_overlapping_exception_wins(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    run_contract_extraction_inline,
    db_session_factory,
) -> None:
    """Code review (2026-10-12): nothing stops granting a second active exception for the
    same rule+target while the first is still valid (e.g. legal re-grants/extends before
    expiry). `execute_review` must deterministically cite exactly one of them, not
    whichever the database happened to return first -- the most recently granted one."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, "exc-overlap-flow@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="exc-overlap-flow-legal@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])

    first = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "contract_version_id": contract_version_id,
            "justification": "First grant.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        _exceptions_url(policy_id, version_id, rule_id),
        json={
            "contract_version_id": contract_version_id,
            "justification": "Second, more recent grant -- should be the one cited.",
            "valid_until": _FUTURE,
        },
        headers=legal_headers,
    )
    assert second.status_code == 201, second.text

    review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=admin_headers,
    )
    assert review.status_code == 201, review.text
    detail = await client.get(
        f"/api/compliance/reviews/{review.json()['id']}", headers=admin_headers
    )
    [fin_003] = [e for e in detail.json()["rule_evaluations"] if e["rule_key"] == "FIN-003"]
    assert fin_003["exception_id"] == second.json()["id"]


async def test_an_expired_exception_is_never_picked_up_for_evaluation(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    run_contract_extraction_inline,
    db_session_factory,
) -> None:
    """`grant_exception` itself refuses a past `valid_until` (see the dedicated negative
    test above); this proves the READ side (`PolicyExceptionRepository.
    list_active_for_rule_ids`) also correctly excludes a row that has since lapsed,
    regardless of how it got into that state. Inserted directly via the repository,
    bypassing the service's own future-only guard -- the one way to simulate a grant
    that has since expired without manipulating wall-clock time."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    admin_headers = await register_org_and_login(client, "exc-expired-flow@example.com")
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    policy_id, version_id, rule_id = await _create_policy_with_rule(
        client, admin_headers, rule_yaml=FIN_003_YAML
    )
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])

    from app.identity.infrastructure.repositories import UserRepository

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("exc-expired-flow@example.com")
        PolicyExceptionRepository(session).add(
            PolicyException(
                organization_id=admin.organization_id,
                rule_id=uuid.UUID(rule_id),
                contract_version_id=uuid.UUID(contract_version_id),
                justification="Already expired by the time the review runs.",
                approver_role="legal",
                granted_by=admin.id,
                valid_until=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()

    review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=admin_headers,
    )
    assert review.status_code == 201, review.text
    assert review.json()["status"] == "REVIEW"
