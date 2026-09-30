"""#61: the simulation / dry-run endpoint -- runs a PolicyVersion's rules against real
`ContractVersion`s (with their linked `Supplier` evidence) and returns per-rule +
aggregate-preview results, with no `ComplianceReview`/`Decision`/audit-event side effect.
"""

import httpx

from tests.policies.conftest import ACTIVE_CNPJ_RESPONSE, create_supplier, pdf_bytes_with_text
from tests.suppliers.conftest import register_org_and_login

TAX_ID = "00000000000191"

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

LEGAL_008_YAML = """
rule:
  id: LEGAL-008
  name: Unlimited Liability Requires Legal Review
when:
  contract.liability.type: unlimited
result:
  status: REVIEW
severity: high
approver_role: legal
"""

SIMULATION_ENVELOPE = {
    "fields": {
        "value": {
            "amount": {
                "value": 300000,
                "confidence": 0.95,
                "provenance": {"document_id": "x", "page": 1, "text_span": {"start": 0, "end": 5}},
            },
            "currency": {
                "value": "BRL",
                "confidence": 0.95,
                "provenance": {"document_id": "x", "page": 1, "text_span": {"start": 5, "end": 8}},
            },
        },
        "liability": {
            "type": {
                "value": "unlimited",
                "confidence": 0.93,
                "provenance": {"document_id": "x", "page": 2, "text_span": {"start": 0, "end": 10}},
            }
        },
    },
    "clauses": [],
}


async def _setup_policy_with_rules(client: httpx.AsyncClient, headers: dict) -> tuple[str, str]:
    created = (
        await client.post("/api/policies", json={"name": "Vendor Policy"}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]
    for rule_yaml in (SANC_001_YAML, FIN_003_YAML, LEGAL_008_YAML):
        response = await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": rule_yaml},
            headers=headers,
        )
        assert response.status_code == 201, response.text
    return policy_id, version_id


async def test_simulate_against_a_sanctioned_supplier_and_high_value_contract(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=SIMULATION_ENVELOPE)

    headers = await register_org_and_login(client, "simulate-1@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)

    upload = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={
                "supplier_id": supplier["id"],
                "title": "High-Value MSA",
                "contract_type": "msa",
            },
            headers=headers,
        )
    ).json()
    contract_version_id = upload["id"]

    policy_id, version_id = await _setup_policy_with_rules(client, headers)

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/simulate",
        json={"contract_version_ids": [contract_version_id]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["version_status"] == "draft"  # simulating a draft version is allowed
    assert len(body["contract_results"]) == 1
    result = body["contract_results"][0]
    assert result["contract_version_id"] == contract_version_id

    outcomes = {e["rule_key"]: e["outcome"] for e in result["rule_evaluations"]}
    assert outcomes["SANC-001"] == "BLOCK"
    assert outcomes["FIN-003"] == "REVIEW"
    assert outcomes["LEGAL-008"] == "REVIEW"

    # ADR-010 §2: any BLOCK wins the aggregation, regardless of the REVIEW rules.
    assert result["aggregate"]["status"] == "BLOCK"


async def test_simulate_has_no_persistent_side_effects(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Running the same simulation twice must produce identical results -- nothing about
    the second run's evaluation was affected by the first (no ComplianceReview/
    RuleEvaluation/Decision row was created, no rule/policy state mutated)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=SIMULATION_ENVELOPE)

    headers = await register_org_and_login(client, "simulate-2@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    upload = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    contract_version_id = upload["id"]
    policy_id, version_id = await _setup_policy_with_rules(client, headers)

    payload = {"contract_version_ids": [contract_version_id]}
    first = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/simulate", json=payload, headers=headers
    )
    second = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/simulate", json=payload, headers=headers
    )
    assert first.json() == second.json()

    # The version is still draft -- simulating never publishes/freezes anything.
    version = (
        await client.get(f"/api/policies/{policy_id}/versions/{version_id}", headers=headers)
    ).json()
    assert version["status"] == "draft"
    rules = (
        await client.get(f"/api/policies/{policy_id}/versions/{version_id}/rules", headers=headers)
    ).json()
    assert all(r["is_frozen"] is False for r in rules)


async def test_simulate_contract_without_supplier_evidence_is_not_applicable(
    client: httpx.AsyncClient,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """A supplier whose initial check hasn't completed (stubbed no-op by default, no
    `run_supplier_checks_inline` requested here) yields no `supplier.*` evidence --
    SANC-001 must come back NOT_APPLICABLE, never a silently-wrong PASS/BLOCK."""
    mock_openrouter(payload=SIMULATION_ENVELOPE)
    headers = await register_org_and_login(client, "simulate-3@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    upload = (
        await client.post(
            "/api/contracts/upload",
            files={"file": ("contract.pdf", pdf_bytes_with_text(), "application/pdf")},
            data={"supplier_id": supplier["id"], "title": "MSA", "contract_type": "msa"},
            headers=headers,
        )
    ).json()
    policy_id, version_id = await _setup_policy_with_rules(client, headers)

    response = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/simulate",
        json={"contract_version_ids": [upload["id"]]},
        headers=headers,
    )
    outcomes = {
        e["rule_key"]: e["outcome"]
        for e in response.json()["contract_results"][0]["rule_evaluations"]
    }
    assert outcomes["SANC-001"] == "NOT_APPLICABLE"
    # The contract-side rules are still fully evaluable regardless of supplier evidence.
    assert outcomes["FIN-003"] == "REVIEW"
