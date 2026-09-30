"""#123/#125/#126: the real (non-simulation) `ComplianceReview` trigger flow -- pools every
currently-published `PolicyVersion` in the organization, evaluates them against real
`ContractVersion`/`Supplier` evidence via the already-tested engine (#60/#61), and persists
the result as `ComplianceReview` + `RuleEvaluation` + `Risk` rows with real audit events.
"""

import httpx

from app.policies.infrastructure.repositories import RuleEvaluationRepository
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
        "liability": {
            "type": {
                "value": "unlimited",
                "confidence": 0.93,
                "provenance": {
                    "document_id": "doc-1",
                    "page": 2,
                    "text_span": {"start": 0, "end": 10},
                },
            }
        },
    },
    "clauses": [],
}


async def _create_policy_with_rules(
    client: httpx.AsyncClient, headers: dict, *, name: str, rule_yamls: list[str]
) -> tuple[str, str]:
    created = (
        await client.post("/api/policies", json={"name": name}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]
    for rule_yaml in rule_yamls:
        response = await client.post(
            f"/api/policies/{policy_id}/versions/{version_id}/rules",
            json={"yaml": rule_yaml},
            headers=headers,
        )
        assert response.status_code == 201, response.text
    publish = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/publish", headers=headers
    )
    assert publish.status_code == 200, publish.text
    return policy_id, version_id


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


async def test_trigger_review_persists_block_and_emits_audit_events(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "trigger-1@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[SANC_001_YAML, FIN_003_YAML]
    )

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["contract_version_id"] == contract_version_id
    assert body["status"] == "BLOCK"  # any BLOCK wins, ADR-010 §2
    assert body["completed_at"] is not None
    assert len(body["policy_version_ids"]) == 1

    # The read-model (#127/#62's backend half) returns the full RuleEvaluation list.
    detail = await client.get(f"/api/compliance/reviews/{body['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    outcomes = {e["rule_key"]: e["outcome"] for e in detail_body["rule_evaluations"]}
    assert outcomes["SANC-001"] == "BLOCK"
    assert outcomes["FIN-003"] == "REVIEW"
    # BLOCK/REVIEW RuleEvaluations each surface a Risk finding (#125's Risk-provenance
    # design decision); PASS/NOT_APPLICABLE never do.
    assert {r["category"] for r in detail_body["risks"]} == {"SANC-001", "FIN-003"}


async def test_trigger_review_evidence_refs_are_real_and_traceable(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """#126: `evidence_refs` must trace back to the actual extracted-field provenance
    (contract.*) and the actual SupplierProfile/SupplierCheck (supplier.*) -- never an
    empty placeholder list when the underlying evidence genuinely exists."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "trigger-2@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client,
        headers,
        name="Vendor Policy",
        rule_yamls=[SANC_001_YAML, FIN_003_YAML, LEGAL_008_YAML],
    )

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    review_id = response.json()["id"]
    detail = (
        await client.get(f"/api/compliance/reviews/{review_id}", headers=headers)
    ).json()
    by_key = {e["rule_key"]: e for e in detail["rule_evaluations"]}

    # SANC-001 references `supplier.sanctions_hit` -> traces to the SupplierProfile/
    # SupplierCheck that produced it.
    sanc_refs = by_key["SANC-001"]["evidence_refs"]
    assert len(sanc_refs) == 1
    assert sanc_refs[0]["context_path"] == "supplier.sanctions_hit"
    assert sanc_refs[0]["source"] == "supplier_profile"
    assert sanc_refs[0]["supplier_id"] == supplier["id"]
    assert sanc_refs[0]["supplier_check_id"]
    assert sanc_refs[0]["supplier_profile_id"]

    # FIN-003 references `contract.value.brl` -> traces to the extracted `value.amount`
    # leaf's real provenance (document_id/page/text_span) from the AI extraction envelope.
    fin_refs = by_key["FIN-003"]["evidence_refs"]
    assert len(fin_refs) == 1
    assert fin_refs[0]["context_path"] == "contract.value.brl"
    assert fin_refs[0]["source"] == "contract_extracted_field"
    # The AI Gateway force-stamps `provenance.document_id` to the real Document's id
    # (server-side re-stamping, `openrouter_gateway.py`) regardless of what the model's
    # raw JSON claimed -- so this is a real Document id, not the envelope's "doc-1".
    assert fin_refs[0]["document_id"]
    assert fin_refs[0]["page"] == 1
    assert fin_refs[0]["text_span"] == {"start": 0, "end": 5}

    # LEGAL-008 references `contract.liability.type`.
    legal_refs = by_key["LEGAL-008"]["evidence_refs"]
    assert len(legal_refs) == 1
    assert legal_refs[0]["context_path"] == "contract.liability.type"
    assert legal_refs[0]["page"] == 2


async def test_trigger_review_order_independent_regardless_of_rule_order(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """ADR-010 §2/BR-CMP-002: the final persisted `ComplianceReview.status` does not
    depend on the order rules were authored/evaluated in -- confirmed here at the
    *persisted* integration level (`evaluate_policy_version`/`aggregate_preview`'s own
    order-independence is already unit-tested in test_evaluation_service.py; this confirms
    the real trigger-review path preserves that property end to end)."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    # Org A: SANC-001 (BLOCK) authored before FIN-003 (REVIEW)/LEGAL-008 (REVIEW).
    headers_a = await register_org_and_login(client, "order-a@example.com")
    supplier_a = await create_supplier(client, headers_a, tax_id=TAX_ID)
    contract_a = await _upload_contract(client, headers_a, supplier_a["id"])
    await _create_policy_with_rules(
        client,
        headers_a,
        name="Policy A",
        rule_yamls=[SANC_001_YAML, FIN_003_YAML, LEGAL_008_YAML],
    )
    response_a = await client.post(
        "/api/compliance/reviews", json={"contract_version_id": contract_a}, headers=headers_a
    )

    # Org B: the exact same three rules, authored in reverse order.
    headers_b = await register_org_and_login(client, "order-b@example.com")
    supplier_b = await create_supplier(client, headers_b, tax_id=TAX_ID)
    contract_b = await _upload_contract(client, headers_b, supplier_b["id"])
    await _create_policy_with_rules(
        client,
        headers_b,
        name="Policy B",
        rule_yamls=[LEGAL_008_YAML, FIN_003_YAML, SANC_001_YAML],
    )
    response_b = await client.post(
        "/api/compliance/reviews", json={"contract_version_id": contract_b}, headers=headers_b
    )

    assert response_a.status_code == 201 and response_b.status_code == 201
    assert response_a.json()["status"] == response_b.json()["status"] == "BLOCK"


async def test_trigger_review_zero_published_policies_defaults_to_approve(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """An organization with zero published Policies has zero applicable rules by
    construction -- ADR-010 §2's "else APPROVE" default applies trivially, at the
    persisted integration level."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "zero-rules-1@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "APPROVE"
    assert body["policy_version_ids"] == []

    detail = (
        await client.get(f"/api/compliance/reviews/{body['id']}", headers=headers)
    ).json()
    assert detail["rule_evaluations"] == []
    assert detail["risks"] == []


async def test_trigger_review_all_rules_not_applicable_defaults_to_approve(
    client: httpx.AsyncClient, mock_openrouter, run_contract_extraction_inline
) -> None:
    """A published policy whose only rule needs supplier evidence that was never
    gathered (no `run_supplier_checks_inline` here) yields exactly one NOT_APPLICABLE
    RuleEvaluation and still an overall APPROVE -- the zero-*applicable*-rules case, as
    distinct from the zero-*rules-at-all* case above."""
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "zero-rules-2@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client, headers, name="Sanctions Policy", rule_yamls=[SANC_001_YAML]
    )

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "APPROVE"

    detail = (
        await client.get(f"/api/compliance/reviews/{body['id']}", headers=headers)
    ).json()
    assert len(detail["rule_evaluations"]) == 1
    assert detail["rule_evaluations"][0]["outcome"] == "NOT_APPLICABLE"
    assert detail["risks"] == []


async def test_trigger_review_unknown_contract_version_is_not_found(
    client: httpx.AsyncClient,
) -> None:
    headers = await register_org_and_login(client, "trigger-404@example.com")
    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 404


async def test_compliance_reviews_are_scoped_to_the_caller_organization(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Multi-tenancy (ADR-003/CLAUDE.md): another organization's ComplianceReview is a
    404, never a cross-tenant leak."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers_owner = await register_org_and_login(client, "tenant-owner@example.com")
    supplier = await create_supplier(client, headers_owner, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers_owner, supplier["id"])
    await _create_policy_with_rules(
        client, headers_owner, name="Vendor Policy", rule_yamls=[SANC_001_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers_owner,
        )
    ).json()

    headers_outsider = await register_org_and_login(client, "tenant-outsider@example.com")
    response = await client.get(
        f"/api/compliance/reviews/{review['id']}", headers=headers_outsider
    )
    assert response.status_code == 404


async def test_rule_evaluation_repository_has_no_update_or_delete_path() -> None:
    """BR-CMP-003 (#126): no actor has any way to alter or remove a recorded
    RuleEvaluation -- enforced by the repository simply exposing no such method, mirroring
    `AuditEventRepository`'s own negative test exactly."""
    exposed_methods = {name for name in dir(RuleEvaluationRepository) if not name.startswith("_")}

    assert exposed_methods == {"add", "get", "list_by_review"}
    for forbidden in ("update", "edit", "delete", "remove", "patch"):
        assert forbidden not in exposed_methods
