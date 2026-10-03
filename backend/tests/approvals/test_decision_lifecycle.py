"""FEATURE-6.5 items 1 and 2 (BR-DEC-002): one effective (`ACTIVE`) Decision per
ContractVersion, enforced by the database. A newer Decision supersedes the previous effective
one in the same transaction -- whether it comes from a manual review, from a re-evaluation
chain that completes later, or from a re-evaluation against a newer ContractVersion.
"""

import uuid
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.application.decision_service import create_decision_for_review
from app.approvals.application.reevaluation_service import reevaluate_stale_decisions
from app.approvals.domain.errors import (
    DecisionAlreadyExistsError,
    DecisionNotFoundError,
    DecisionReviewNotFoundError,
)
from app.approvals.infrastructure.models import Decision
from app.policies.infrastructure.models import ComplianceReview
from tests.approvals.conftest import ACTIVE_CNPJ_RESPONSE, create_supplier, register_org_and_login
from tests.approvals.lifecycle_helpers import (
    active_decisions_for_version,
    approve_pending_for,
    audit_events,
    decision_row,
    finance_review_chain,
    superseding_review_ids,
)
from tests.approvals.test_reevaluation import (
    _decisions_of,
    _expire_decision,
    _org_id,
    _successor_of,
    _upload_version,
    _version_row,
    _zero_policy_decision,
)
from tests.policies.test_compliance_review import EVIDENCE_ENVELOPE, TAX_ID, _upload_contract


async def test_database_allows_only_one_active_decision_per_contract_version(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The partial unique index, exercised directly: a second ACTIVE row for the same
    ContractVersion is refused by the database, while a SUPERSEDED one is allowed."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "lifecycle-index@example.com")
    _, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "lifecycle-index@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    assert original.lifecycle == "ACTIVE"

    async def _second_decision(lifecycle: str) -> None:
        async with db_session_factory() as session:
            review = ComplianceReview(
                organization_id=organization_id,
                contract_version_id=uuid.UUID(contract_version_id),
                policy_version_ids=[],
                status="APPROVE",
            )
            session.add(review)
            await session.flush()
            session.add(
                Decision(
                    organization_id=organization_id,
                    compliance_review_id=review.id,
                    contract_version_id=uuid.UUID(contract_version_id),
                    lifecycle=lifecycle,
                    status="APPROVE",
                    valid_until=datetime.now(UTC),
                )
            )
            await session.flush()

    with pytest.raises(IntegrityError):
        await _second_decision("ACTIVE")
    await _second_decision("SUPERSEDED")


async def test_second_manual_review_on_the_same_version_supersedes_the_first(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "lifecycle-manual@example.com")
    _, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "lifecycle-manual@example.com")
    [first] = await _decisions_of(db_session_factory, organization_id)

    second_review = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert second_review.status_code == 201, second_review.text

    [active] = await active_decisions_for_version(
        db_session_factory, uuid.UUID(contract_version_id)
    )
    first_after = await decision_row(db_session_factory, first.id)
    assert first_after.lifecycle == "SUPERSEDED"
    assert active.id != first.id
    assert active.lifecycle == "ACTIVE"
    assert active.supersedes_decision_id == first.id
    # Content of the superseded Decision is untouched (BR-DEC-002).
    assert first_after.status == first.status
    assert first_after.valid_until == first.valid_until
    assert first_after.overridden is False

    # A manual review carries no re-evaluation link of its own; the supersession is recorded
    # on the Decision and in the decision.created payload.
    created = [
        e
        for e in await audit_events(db_session_factory, organization_id, "decision.created")
        if e.payload["decision_id"] == str(active.id)
    ]
    assert created[0].payload["superseded_decision_ids"] == [str(first.id)]


async def test_manual_review_completing_before_a_pending_reevaluation_chain_is_superseded_by_it(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Ordering A: a manual review (REVIEW chain) is opened while a re-evaluation chain is
    still pending. The manual chain resolves FIRST, so its Decision supersedes the original;
    when the re-evaluation chain resolves LAST, its Decision supersedes whatever is ACTIVE at
    that moment -- the manual one -- not the original it was triggered against."""
    chain = await _reevaluation_chain_with_manual_review(
        client,
        db_session_factory,
        email="lifecycle-order-a@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    await approve_pending_for(
        client, chain["legal_headers"], chain["admin_headers"], chain["manual_review_id"]
    )
    await approve_pending_for(
        client, chain["legal_headers"], chain["admin_headers"], chain["reeval_review_id"]
    )

    active = await active_decisions_for_version(
        db_session_factory, uuid.UUID(chain["contract_version_id"])
    )
    assert len(active) == 1
    assert active[0].compliance_review_id == uuid.UUID(chain["reeval_review_id"])
    assert active[0].supersedes_decision_id == chain["original_decision_id"]
    manual = await _decision_for_review(db_session_factory, chain["manual_review_id"])
    assert manual.lifecycle == "SUPERSEDED"
    original = await decision_row(db_session_factory, chain["original_decision_id"])
    assert original.lifecycle == "SUPERSEDED"


async def test_reevaluation_chain_completing_before_a_pending_manual_review_is_superseded_by_it(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Ordering B: the mirror image. The re-evaluation chain resolves first; the manual
    review's Decision, created last, supersedes it."""
    chain = await _reevaluation_chain_with_manual_review(
        client,
        db_session_factory,
        email="lifecycle-order-b@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    await approve_pending_for(
        client, chain["legal_headers"], chain["admin_headers"], chain["reeval_review_id"]
    )
    await approve_pending_for(
        client, chain["legal_headers"], chain["admin_headers"], chain["manual_review_id"]
    )

    active = await active_decisions_for_version(
        db_session_factory, uuid.UUID(chain["contract_version_id"])
    )
    assert len(active) == 1
    assert active[0].compliance_review_id == uuid.UUID(chain["manual_review_id"])
    reeval = await _decision_for_review(db_session_factory, chain["reeval_review_id"])
    assert reeval.lifecycle == "SUPERSEDED"
    original = await decision_row(db_session_factory, chain["original_decision_id"])
    assert original.lifecycle == "SUPERSEDED"


async def test_reevaluation_against_a_newer_contract_version_supersedes_its_predecessor(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """The predecessor belongs to the OLDER ContractVersion, so "the ACTIVE Decision for the new
    version" finds nothing. It must still be superseded by name, or it would stay ACTIVE forever
    alongside its successor."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "lifecycle-cross-version@example.com")
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    v1_id = await _upload_contract(client, headers, supplier["id"])
    await client.post(
        "/api/compliance/reviews", json={"contract_version_id": v1_id}, headers=headers
    )
    organization_id = await _org_id(db_session_factory, "lifecycle-cross-version@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    v1_row = await _version_row(db_session_factory, uuid.UUID(v1_id))
    v2 = await _upload_version(
        client, headers, supplier_id=supplier["id"], contract_id=str(v1_row.contract_id)
    )
    assert (await _version_row(db_session_factory, uuid.UUID(v2["id"]))).status == "analyzed"

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1

    successor = await _successor_of(db_session_factory, original.id)
    assert successor is not None
    assert str(successor.contract_version_id) == v2["id"]
    assert (await decision_row(db_session_factory, original.id)).lifecycle == "SUPERSEDED"
    assert [
        d.id for d in await active_decisions_for_version(db_session_factory, uuid.UUID(v2["id"]))
    ] == [successor.id]
    assert await active_decisions_for_version(db_session_factory, uuid.UUID(v1_id)) == []


async def test_a_foreign_review_or_predecessor_is_refused_and_touches_nothing(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """Tenant isolation for the supersede-on-create path (ADR-003): organization A cannot
    package organization B's review, and cannot name B's Decision as the predecessor. Either
    refusal happens before any row is written, so both organizations' effective Decisions
    are unchanged."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers_a = await register_org_and_login(client, "lifecycle-tenant-a@example.com")
    headers_b = await register_org_and_login(client, "lifecycle-tenant-b@example.com")
    _, version_a = await _zero_policy_decision(client, headers_a)
    _, version_b = await _zero_policy_decision(client, headers_b)
    org_a = await _org_id(db_session_factory, "lifecycle-tenant-a@example.com")
    org_b = await _org_id(db_session_factory, "lifecycle-tenant-b@example.com")
    [decision_a] = await _decisions_of(db_session_factory, org_a)
    [decision_b] = await _decisions_of(db_session_factory, org_b)
    review_b_id = decision_b.compliance_review_id

    async with db_session_factory() as session:
        with pytest.raises(DecisionReviewNotFoundError):
            await create_decision_for_review(
                session,
                organization_id=org_a,
                actor_id=None,
                compliance_review_id=review_b_id,
                status="BLOCK",
            )
        await session.rollback()

    async with db_session_factory() as session:
        with pytest.raises(DecisionNotFoundError):
            await create_decision_for_review(
                session,
                organization_id=org_b,
                actor_id=None,
                compliance_review_id=review_b_id,
                status="BLOCK",
                supersedes_decision_id=decision_a.id,
            )
        await session.rollback()

    assert (await decision_row(db_session_factory, decision_a.id)).lifecycle == "ACTIVE"
    assert (await decision_row(db_session_factory, decision_b.id)).lifecycle == "ACTIVE"
    assert len(await _decisions_of(db_session_factory, org_a)) == 1
    assert len(await _decisions_of(db_session_factory, org_b)) == 1
    assert await active_decisions_for_version(db_session_factory, uuid.UUID(version_a))
    assert await active_decisions_for_version(db_session_factory, uuid.UUID(version_b))


async def _reevaluation_chain_with_manual_review(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    *,
    email: str,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
) -> dict:
    """Builds the shared shape of both orderings: an APPROVE original is made stale (expired),
    its re-evaluation opens a REVIEW chain, and then a MANUAL review of the same version opens
    a second REVIEW chain while the first is still pending. Both chains are left pending for
    the test to resolve in whichever order it is checking."""
    chain = await finance_review_chain(
        client,
        db_session_factory,
        email=email,
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
    )
    await _expire_decision(db_session_factory, chain["decision_id"])

    async with db_session_factory() as session:
        assert await reevaluate_stale_decisions(session) == 1
    [reeval_review_id] = await superseding_review_ids(db_session_factory, chain["decision_id"])

    manual = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": str(chain["contract_version_id"])},
        headers=chain["admin_headers"],
    )
    assert manual.status_code == 201, manual.text
    assert manual.json()["status"] == "REVIEW"

    return {
        "admin_headers": chain["admin_headers"],
        "legal_headers": chain["legal_headers"],
        "contract_version_id": str(chain["contract_version_id"]),
        "original_decision_id": chain["decision_id"],
        "reeval_review_id": str(reeval_review_id),
        "manual_review_id": manual.json()["id"],
    }


async def _decision_for_review(db_session_factory: async_sessionmaker, review_id: str) -> Decision:
    async with db_session_factory() as session:
        return (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == uuid.UUID(review_id))
            )
        ).scalar_one()


def _row_state(decision: Decision) -> dict:
    """Every column a superseded or overridden-but-historical row must keep unchanged."""
    return {
        "lifecycle": decision.lifecycle,
        "status": decision.status,
        "overridden": decision.overridden,
        "override_justification": decision.override_justification,
        "valid_until": decision.valid_until,
        "supersedes_decision_id": decision.supersedes_decision_id,
        "review_required_at": decision.review_required_at,
        "reevaluation_generation": decision.reevaluation_generation,
    }


async def test_a_superseded_decision_cannot_be_overridden_and_its_row_is_unchanged(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """F1(a): the override is a conditional UPDATE on `lifecycle = ACTIVE`. A superseded Decision
    matches no row, so it is refused with 409 and nothing is written."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "override-superseded@example.com")
    _, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "override-superseded@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    second = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert second.status_code == 201, second.text
    before = await decision_row(db_session_factory, original.id)
    assert before.lifecycle == "SUPERSEDED"

    refused = await client.post(
        f"/api/decisions/{original.id}/override",
        json={"new_status": "REVIEW", "justification": "Too late, it was already replaced"},
        headers=headers,
    )
    assert refused.status_code == 409, refused.text

    after = await decision_row(db_session_factory, original.id)
    assert _row_state(after) == _row_state(before)
    assert await audit_events(db_session_factory, organization_id, "decision.overridden") == []


async def test_a_manual_review_may_still_replace_an_overridden_active_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """F1(b), the allowed side: replacing an override is a human action. A manual review carries
    no supersedes link, so it supersedes an overridden ACTIVE Decision and the override stays on the
    historical row, untouched."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "manual-replaces-override@example.com")
    _, contract_version_id = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "manual-replaces-override@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)
    justification = "Accepted by the CFO; revisit at the next review"
    overridden = await client.post(
        f"/api/decisions/{original.id}/override",
        json={"new_status": "REVIEW", "justification": justification},
        headers=headers,
    )
    assert overridden.status_code == 200, overridden.text

    manual = await client.post(
        "/api/compliance/reviews",
        json={"contract_version_id": contract_version_id},
        headers=headers,
    )
    assert manual.status_code == 201, manual.text

    historical = await decision_row(db_session_factory, original.id)
    assert historical.lifecycle == "SUPERSEDED"
    assert historical.overridden is True
    assert historical.override_justification == justification
    [active] = await active_decisions_for_version(
        db_session_factory, uuid.UUID(contract_version_id)
    )
    assert active.supersedes_decision_id == original.id


@pytest.mark.parametrize(
    ("driver_message", "expected"),
    [
        # A foreign-key failure is a bug in this insert, never a duplicate: it must surface.
        ("FOREIGN KEY constraint failed", IntegrityError),
        # A uniqueness violation on some other table is not the Decision's either.
        ("UNIQUE constraint failed: users.email", IntegrityError),
        # The two known constraints are the only ones mapped to a 409.
        (
            "UNIQUE constraint failed: decisions.compliance_review_id",
            DecisionAlreadyExistsError,
        ),
    ],
)
async def test_only_the_known_uniqueness_constraints_map_to_already_exists(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
    monkeypatch: pytest.MonkeyPatch,
    driver_message: str,
    expected: type[Exception],
) -> None:
    """F6: `create_decision_for_review` used to map EVERY IntegrityError to
    DecisionAlreadyExistsError. Only the two known uniqueness constraints may be mapped now."""
    mock_cnpj_registry(data=ACTIVE_CNPJ_RESPONSE)
    await seed_sanctions_index(hit_document=TAX_ID)
    mock_openrouter(payload=EVIDENCE_ENVELOPE)

    headers = await register_org_and_login(client, "integrity-mapping@example.com")
    _, _ = await _zero_policy_decision(client, headers)
    organization_id = await _org_id(db_session_factory, "integrity-mapping@example.com")
    [original] = await _decisions_of(db_session_factory, organization_id)

    async with db_session_factory() as session:
        review_id = original.compliance_review_id

        async def _failing_flush(*_args, **_kwargs):
            raise IntegrityError("INSERT INTO decisions", {}, Exception(driver_message))

        monkeypatch.setattr(session, "flush", _failing_flush)
        with pytest.raises(expected) as raised:
            await create_decision_for_review(
                session,
                organization_id=organization_id,
                actor_id=None,
                compliance_review_id=review_id,
                status="BLOCK",
            )
        if expected is IntegrityError:
            assert type(raised.value) is IntegrityError
    assert len(await _decisions_of(db_session_factory, organization_id)) == 1
