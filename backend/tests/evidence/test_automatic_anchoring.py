"""#199: automatic anchor submission, enqueued right after each of `create_decision_for_
review`'s call sites commits -- the synchronous APPROVE/BLOCK path
(`compliance_review_service.trigger_review`), `approval_service.approve_request`/
`reject_request` once a REVIEW chain resolves. Driven through the real endpoints, using the
`submit_anchor_inline` opt-in fixture (`tests/conftest.py`) to run the enqueued submission
synchronously against the test database instead of requiring a real Celery worker.
"""

import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application import reevaluation_service
from app.approvals.application.reevaluation_service import reevaluate_stale_decisions
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.evidence.infrastructure.models import BlockchainAnchor, EvidencePackage
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import (
    ACTIVE_CNPJ_RESPONSE,
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.approvals.lifecycle_helpers import approve_pending_for, pending_request_for
from tests.approvals.test_reevaluation import _expire_decision, _org_id, _zero_policy_decision
from tests.evidence.test_evidence_package import _block_review
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    FIN_003_YAML,
    SANC_001_YAML,
    TAX_ID,
    _create_policy_with_rules,
    _upload_contract,
)


async def _anchor_for_decision(
    db_session_factory: async_sessionmaker, decision_id: uuid.UUID
) -> BlockchainAnchor | None:
    async with db_session_factory() as session:
        package = (
            await session.execute(
                select(EvidencePackage).where(EvidencePackage.decision_id == decision_id)
            )
        ).scalar_one()
        return (
            await session.execute(
                select(BlockchainAnchor).where(
                    BlockchainAnchor.evidence_package_id == package.id
                )
            )
        ).scalar_one_or_none()


async def test_synchronous_approve_decision_is_automatically_anchored(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    submit_anchor_inline,
) -> None:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "auto-anchor-approve@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "APPROVE"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-approve@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )

    anchor = await _anchor_for_decision(db_session_factory, decision.id)
    assert anchor is not None
    assert anchor.status == "confirmed"


async def test_synchronous_block_decision_is_automatically_anchored(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    submit_anchor_inline,
) -> None:
    headers, _, review_id = await _block_review(
        client,
        db_session_factory,
        email="auto-anchor-block@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-block@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review_id), admin.organization_id
        )

    anchor = await _anchor_for_decision(db_session_factory, decision.id)
    assert anchor is not None


async def test_review_outcome_has_no_decision_and_no_anchor_until_the_chain_resolves(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    submit_anchor_inline,
) -> None:
    """A REVIEW outcome has no Decision (and so no EvidencePackage/anchor) yet -- confirms
    the trigger_review call site correctly does NOT enqueue anything for this branch."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "auto-anchor-pending@example.com")
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    await _create_policy_with_rules(
        client, admin_headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=admin_headers,
        )
    ).json()
    assert review["status"] == "REVIEW"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-pending@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    assert decision is None


async def test_approve_request_terminal_step_is_automatically_anchored(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    submit_anchor_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "auto-anchor-chain@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="legal-auto-anchor-chain@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    await _create_policy_with_rules(
        client, admin_headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=admin_headers,
        )
    ).json()
    assert review["status"] == "REVIEW"

    await approve_pending_for(client, legal_headers, admin_headers, review["id"])

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-chain@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    assert decision.status == "APPROVE"

    anchor = await _anchor_for_decision(db_session_factory, decision.id)
    assert anchor is not None


async def test_reject_request_is_automatically_anchored(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    submit_anchor_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    admin_headers = await register_org_and_login(client, "auto-anchor-reject@example.com")
    legal_headers = await create_user_and_login(
        client, admin_headers, email="legal-auto-anchor-reject@example.com", role="legal"
    )
    supplier = await create_supplier(client, admin_headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, admin_headers, supplier["id"])
    await _create_policy_with_rules(
        client, admin_headers, name="Vendor Policy", rule_yamls=[FIN_003_YAML]
    )
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=admin_headers,
        )
    ).json()
    assert review["status"] == "REVIEW"

    pending = await pending_request_for(client, admin_headers, review["id"])
    rejected = await client.post(
        f"/api/approvals/requests/{pending['id']}/reject",
        json={"justification": "rejected in test"},
        headers=legal_headers,
    )
    assert rejected.status_code == 200, rejected.text

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-reject@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )
    assert decision.status == "BLOCK"

    anchor = await _anchor_for_decision(db_session_factory, decision.id)
    assert anchor is not None


async def test_without_the_inline_fixture_no_anchor_is_created(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """The default (`stub_anchor_submission_enqueue`, autouse) must not create a real anchor
    -- confirms every other test in this suite isn't accidentally exercising a real Celery
    broker/worker just by creating a Decision."""
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, "auto-anchor-default-off@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])

    response = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "APPROVE"

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("auto-anchor-default-off@example.com")
        decision = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), admin.organization_id
        )

    anchor = await _anchor_for_decision(db_session_factory, decision.id)
    assert anchor is None


async def test_reevaluation_sweep_automatically_anchors_the_successor_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    submit_anchor_inline,
) -> None:
    """QA review (2026-10-11): the re-evaluation sweep is the one `enqueue_anchor_submission`
    call site with no API route of its own -- exercised directly against
    `reevaluate_stale_decisions`, the same way `test_reevaluation.py` does."""
    headers = await register_org_and_login(client, "auto-anchor-sweep@example.com")
    review, _ = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "auto-anchor-sweep@example.com")
    async with db_session_factory() as session:
        original = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    await _expire_decision(db_session_factory, original.id)

    async with db_session_factory() as session:
        reevaluated = await reevaluate_stale_decisions(session)
    assert reevaluated == 1

    async with db_session_factory() as session:
        successor = (
            await session.execute(
                select(Decision).where(Decision.supersedes_decision_id == original.id)
            )
        ).scalar_one()

    anchor = await _anchor_for_decision(db_session_factory, successor.id)
    assert anchor is not None


async def test_reevaluation_enqueue_failure_is_not_misattributed_as_a_reevaluation_failure(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QA review (2026-10-11), regression for the exact bug it found: a failure inside
    `enqueue_anchor_submission` must never be recorded as a re-evaluation failure against the
    (already-superseded) original Decision -- the new Decision already committed
    successfully, and `reevaluated` must still count it."""
    headers = await register_org_and_login(client, "auto-anchor-sweep-fail@example.com")
    review, _ = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "auto-anchor-sweep-fail@example.com")
    async with db_session_factory() as session:
        original = await DecisionRepository(session).get_by_review(
            uuid.UUID(review["id"]), organization_id
        )
    await _expire_decision(db_session_factory, original.id)

    async def _boom(**kwargs: object) -> None:
        raise RuntimeError("broker unreachable")

    monkeypatch.setattr(reevaluation_service, "enqueue_anchor_submission", _boom)

    async with db_session_factory() as session:
        reevaluated = await reevaluate_stale_decisions(session)

    assert reevaluated == 1  # the review succeeded; only the enqueue failed

    async with db_session_factory() as session:
        reread_original = await session.get(Decision, original.id)
    assert reread_original.reevaluation_failure_count == 0
    assert reread_original.reevaluation_failed_at is None

    async with db_session_factory() as session:
        successor = (
            await session.execute(
                select(Decision).where(Decision.supersedes_decision_id == original.id)
            )
        ).scalar_one_or_none()
    assert successor is not None  # the successor Decision exists despite the enqueue failure


def test_every_importer_of_enqueue_anchor_submission_is_stubbed_in_conftest() -> None:
    """QA review (2026-10-11): `tests/conftest.py`'s `_ANCHOR_ENQUEUE_CALL_SITES` is a
    hand-maintained tuple, not derived from the import graph -- a future call site added to
    production code without also being added there would silently skip both
    `stub_anchor_submission_enqueue` and `submit_anchor_inline`, making that one test start
    publishing real Celery tasks. This AST-scans every module under `app/` for a direct-name
    import of `enqueue_anchor_submission` and asserts the two sets are exactly equal."""
    import ast
    from pathlib import Path

    from tests.conftest import _ANCHOR_ENQUEUE_CALL_SITES

    app_dir = Path(__file__).resolve().parents[2] / "app"
    importers: set[str] = set()
    for path in app_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            is_target_import = isinstance(node, ast.ImportFrom) and node.module and any(
                alias.name == "enqueue_anchor_submission" for alias in node.names
            )
            if is_target_import:
                # module path -> importable module name, e.g. ".../app/approvals/
                # application/approval_service.py" -> "app.approvals.application.
                # approval_service"
                relative = path.relative_to(app_dir.parent).with_suffix("")
                importers.add(".".join(relative.parts))

    stubbed = {module.__name__ for module in _ANCHOR_ENQUEUE_CALL_SITES}
    assert importers == stubbed, (
        f"enqueue_anchor_submission importers {importers} != "
        f"tests/conftest.py's _ANCHOR_ENQUEUE_CALL_SITES {stubbed}"
    )
