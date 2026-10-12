"""FEATURE-7.2 / STORY-7.2.1: AuditEvents for policy authoring and publication, and for the
ComplianceReview lifecycle (started, one rule_evaluated per rule, completed) [AUD-001]."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.infrastructure.repositories import AuditEventRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import create_user_and_login
from tests.policies.conftest import create_supplier
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)
from tests.suppliers.conftest import ACTIVE_CNPJ_RESPONSE, register_org_and_login

EMAIL = "audit-policy@example.com"


async def _events(db_session_factory: async_sessionmaker, event_type: str) -> list:
    async with db_session_factory() as session:
        return await AuditEventRepository(session).list(event_type=event_type)


async def _user(db_session_factory: async_sessionmaker):
    async with db_session_factory() as session:
        return await UserRepository(session).get_by_email(EMAIL)


async def test_policy_creation_emits_policy_created(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, EMAIL)
    created = (
        await client.post("/api/policies", json={"name": "Vendor Policy"}, headers=headers)
    ).json()
    admin = await _user(db_session_factory)

    [event] = await _events(db_session_factory, "policy.created")
    assert event.actor_id == admin.id
    assert event.organization_id == admin.organization_id
    assert event.payload["policy_id"] == created["policy"]["id"]
    assert event.payload["name"] == "Vendor Policy"


async def test_rule_create_and_update_emit_rule_events(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, EMAIL)
    created = (
        await client.post("/api/policies", json={"name": "Vendor Policy"}, headers=headers)
    ).json()
    policy_id = created["policy"]["id"]
    version_id = created["initial_version"]["id"]

    rule = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules",
        json={"yaml": FIN_003_YAML},
        headers=headers,
    )
    assert rule.status_code == 201, rule.text
    rule_id = rule.json()["id"]

    [created_event] = await _events(db_session_factory, "policy.rule_created")
    assert created_event.payload["rule_id"] == rule_id
    assert created_event.payload["rule_key"] == "FIN-003"
    assert created_event.payload["policy_version_id"] == version_id

    updated = await client.put(
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule_id}",
        json={"yaml": FIN_003_YAML},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    [updated_event] = await _events(db_session_factory, "policy.rule_updated")
    assert updated_event.payload["rule_id"] == rule_id
    assert updated_event.payload["rule_key"] == "FIN-003"


async def test_publish_and_new_draft_emit_version_events(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await register_org_and_login(client, EMAIL)
    policy_id, version_id = await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )

    [published] = await _events(db_session_factory, "policy.version_published")
    assert published.payload["policy_version_id"] == version_id
    assert published.payload["policy_id"] == policy_id

    draft = await client.post(f"/api/policies/{policy_id}/versions", headers=headers)
    assert draft.status_code == 201, draft.text

    [drafted] = await _events(db_session_factory, "policy.version_draft_created")
    assert drafted.payload["policy_version_id"] == draft.json()["id"]
    assert drafted.payload["copied_from_version_id"] == version_id
    assert drafted.payload["version_number"] == 2


async def test_compliance_review_emits_started_one_rule_evaluated_per_rule_and_completed(
    client: httpx.AsyncClient,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    db_session_factory: async_sessionmaker,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, EMAIL)
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    await _create_policy_with_rules(
        client, headers, name="Vendor Policy", rule_yamls=[SANC_001_YAML, FIN_003_YAML]
    )

    review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert review.status_code == 201, review.text
    review_id = review.json()["id"]
    admin = await _user(db_session_factory)

    [started] = await _events(db_session_factory, "compliance.review_started")
    [completed] = await _events(db_session_factory, "compliance.review_completed")
    evaluated = await _events(db_session_factory, "compliance.rule_evaluated")
    assert started.organization_id == admin.organization_id
    assert started.payload["compliance_review_id"] == review_id
    assert completed.payload["compliance_review_id"] == review_id
    assert completed.payload["status"] == "BLOCK"
    assert completed.payload["rule_evaluation_count"] == 2
    assert len(evaluated) == 2
    assert {e.payload["rule_key"] for e in evaluated} == {"SANC-001", "FIN-003"}
    assert all(e.payload["compliance_review_id"] == review_id for e in evaluated)


async def test_grant_exception_emits_policy_exception_granted(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """#120 (STORY-4.4.2)."""
    admin_headers = await register_org_and_login(client, "audit-exception@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="audit-exception-legal@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    created = (
        await client.post("/api/policies", json={"name": "Vendor Policy"}, headers=admin_headers)
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

    valid_until = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    grant = await client.post(
        f"/api/policies/{policy_id}/versions/{version_id}/rules/{rule['id']}/exceptions",
        json={
            "supplier_id": supplier["id"],
            "justification": "Renewal of an already-reviewed MSA.",
            "valid_until": valid_until,
        },
        headers=legal_headers,
    )
    assert grant.status_code == 201, grant.text
    exception_id = grant.json()["id"]

    [event] = await _events(db_session_factory, "policy.exception_granted")
    assert str(event.organization_id) == grant.json()["organization_id"]
    assert event.payload["policy_exception_id"] == exception_id
    assert event.payload["rule_id"] == rule["id"]
    assert event.payload["rule_key"] == "FIN-003"
    assert event.payload["supplier_id"] == supplier["id"]
    assert event.payload["contract_version_id"] is None
    assert event.payload["approver_role"] == "legal"
