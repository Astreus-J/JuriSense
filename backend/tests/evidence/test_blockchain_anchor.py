"""FEATURE-8.2 (STORY-8.2.1, ADR-007): `BlockchainAnchor` creation and the submit/get/recheck
routes, exercised against the real default `AnchoringProvider` (`transparency_log` --
`Settings.anchoring_provider`'s default, since Constellation DED credentials are not
provisioned; see `docs/06-blockchain/anchoring-providers.md`'s spike findings). No network, no
mocking of the provider itself: `tests/evidence/conftest.py`'s `isolated_transparency_log`
fixture points the real adapter at a per-test `tmp_path` repo.

Driven through the real endpoints, matching `test_evidence_package.py`/`test_decision_
passport.py`'s discipline for this package.
"""

import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.evidence.application import anchoring_service
from app.evidence.domain.anchoring import AnchorProof, AnchorStatus
from app.evidence.domain.errors import AnchorAlreadySubmittedError
from app.evidence.infrastructure.models import BlockchainAnchor, EvidencePackage
from app.evidence.infrastructure.repositories import (
    AuditEventRepository,
    BlockchainAnchorRepository,
)
from tests.approvals.conftest import (
    create_supplier,
    create_user_and_login,
    register_org_and_login,
)
from tests.evidence.test_evidence_package import _block_review, _decision_for_review, _package_rows
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    SANC_001_YAML,
    TAX_ID,
    _upload_contract,
)


async def _organization_id_for_package(
    db_session_factory: async_sessionmaker, package_id: uuid.UUID
) -> uuid.UUID:
    async with db_session_factory() as session:
        return (
            await session.execute(
                select(EvidencePackage.organization_id).where(EvidencePackage.id == package_id)
            )
        ).scalar_one()


async def _package_id_for_simple_approval(
    client: httpx.AsyncClient, *, email: str, mock_openrouter, db_session_factory
) -> tuple[dict, uuid.UUID]:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, email)
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    decision = await _decision_for_review(db_session_factory, review["id"])
    [package], _ = await _package_rows(db_session_factory, decision.id)
    return headers, package.id


async def test_submit_anchor_creates_a_confirmed_transparency_log_anchor(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-submit@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )

    response = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["provider"] == "transparency_log"
    assert body["status"] == "confirmed"
    assert body["anchor_ref"]
    assert body["confirmed_at"] is not None
    assert body["proof"]["evidence_hash"]


async def test_submit_anchor_twice_for_the_same_package_is_409(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-twice@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    first = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    assert first.status_code == 201, first.text

    second = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)

    assert second.status_code == 409, second.text


async def test_get_package_anchor_is_null_before_submission_and_populated_after(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-get@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )

    before = await client.get(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    assert before.status_code == 200, before.text
    assert before.json() is None

    submitted = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    after = await client.get(f"/api/evidence-packages/{package_id}/anchor", headers=headers)

    assert after.status_code == 200, after.text
    assert after.json()["id"] == submitted.json()["id"]


async def test_recheck_an_already_confirmed_anchor_is_a_noop(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """The transparency log confirms synchronously, so a recheck afterwards must not
    duplicate the `evidence.anchored` audit event (`_refresh_from_provider`'s
    `newly_confirmed` guard)."""
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-recheck@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    submitted = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    anchor_id = submitted.json()["id"]

    rechecked = await client.post(f"/api/blockchain-anchors/{anchor_id}/recheck", headers=headers)

    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "confirmed"
    async with db_session_factory() as session:
        events = await AuditEventRepository(session).list(event_type="evidence.anchored")
    assert len(events) == 1


async def test_submit_anchor_emits_evidence_anchored_with_the_expected_payload(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-audit@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )

    submitted = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    anchor = submitted.json()

    async with db_session_factory() as session:
        [event] = await AuditEventRepository(session).list(event_type="evidence.anchored")
    assert event.payload["blockchain_anchor_id"] == anchor["id"]
    assert event.payload["evidence_package_id"] == str(package_id)
    assert event.payload["provider"] == "transparency_log"
    assert event.payload["anchor_ref"] == anchor["anchor_ref"]
    assert event.payload["confirmed_at"] is not None


async def test_anchor_payload_never_contains_raw_document_or_personal_data(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    mock_cnpj_registry,
    seed_sanctions_index,
    run_contract_extraction_inline,
    run_supplier_checks_inline,
) -> None:
    """EVD-004/BR-EVD-002, FEATURE-8.2's explicit acceptance criterion: submitting only the
    hash means the supplier's tax id/legal name and the contract's rule-evaluation rationale
    (which quotes contract terms, per `test_evidence_package.py`'s identical check on the raw
    Evidence leaves) must never appear in the persisted BlockchainAnchor row."""
    headers, contract_version_id, review_id = await _block_review(
        client,
        db_session_factory,
        email="anchor-privacy@example.com",
        mock_openrouter=mock_openrouter,
        mock_cnpj_registry=mock_cnpj_registry,
        seed_sanctions_index=seed_sanctions_index,
        rule_yamls=[SANC_001_YAML],
    )
    decision = await _decision_for_review(db_session_factory, review_id)
    [package], _ = await _package_rows(db_session_factory, decision.id)

    response = await client.post(f"/api/evidence-packages/{package.id}/anchor", headers=headers)
    assert response.status_code == 201, response.text
    anchor = response.json()

    serialized = str(anchor)
    assert TAX_ID not in serialized
    assert "Test Supplier Ltda." not in serialized


class TestTenantIsolationAndRbac:
    async def _two_tenants(
        self, client: httpx.AsyncClient, db_session_factory: async_sessionmaker, mock_openrouter
    ) -> tuple[dict, uuid.UUID, dict]:
        headers_a, package_id = await _package_id_for_simple_approval(
            client,
            email="anchor-iso-a@example.com",
            mock_openrouter=mock_openrouter,
            db_session_factory=db_session_factory,
        )
        headers_b = await register_org_and_login(client, "anchor-iso-b@example.com")
        return headers_a, package_id, headers_b

    async def test_submit_anchor_is_404_for_another_tenants_package(
        self,
        client: httpx.AsyncClient,
        db_session_factory: async_sessionmaker,
        mock_openrouter,
        run_contract_extraction_inline,
    ) -> None:
        _, package_id, headers_b = await self._two_tenants(
            client, db_session_factory, mock_openrouter
        )

        response = await client.post(
            f"/api/evidence-packages/{package_id}/anchor", headers=headers_b
        )

        assert response.status_code == 404, response.text

    async def test_get_package_anchor_is_404_for_another_tenants_package(
        self,
        client: httpx.AsyncClient,
        db_session_factory: async_sessionmaker,
        mock_openrouter,
        run_contract_extraction_inline,
    ) -> None:
        _, package_id, headers_b = await self._two_tenants(
            client, db_session_factory, mock_openrouter
        )

        response = await client.get(
            f"/api/evidence-packages/{package_id}/anchor", headers=headers_b
        )

        assert response.status_code == 404, response.text

    async def test_recheck_is_404_for_another_tenants_anchor(
        self,
        client: httpx.AsyncClient,
        db_session_factory: async_sessionmaker,
        mock_openrouter,
        run_contract_extraction_inline,
    ) -> None:
        headers_a, package_id, headers_b = await self._two_tenants(
            client, db_session_factory, mock_openrouter
        )
        submitted = await client.post(
            f"/api/evidence-packages/{package_id}/anchor", headers=headers_a
        )
        anchor_id = submitted.json()["id"]

        response = await client.post(
            f"/api/blockchain-anchors/{anchor_id}/recheck", headers=headers_b
        )

        assert response.status_code == 404, response.text

    async def test_role_without_evidence_update_is_refused_on_submit_but_can_read(
        self,
        client: httpx.AsyncClient,
        db_session_factory: async_sessionmaker,
        mock_openrouter,
        run_contract_extraction_inline,
    ) -> None:
        """RBAC (DEFAULT_ROLE_GRID): submitting is ADMIN-only (Module.EVIDENCE "update"),
        deliberately the narrowest default for a new, externally-facing action -- every
        other Evidence-reading role still has "read", so GET on the (empty) anchor state
        still works for them."""
        headers_a, package_id = await _package_id_for_simple_approval(
            client,
            email="anchor-rbac@example.com",
            mock_openrouter=mock_openrouter,
            db_session_factory=db_session_factory,
        )
        legal_headers = await create_user_and_login(
            client, headers_a, email="legal-anchor-rbac@example.com", role="legal"
        )

        submit_response = await client.post(
            f"/api/evidence-packages/{package_id}/anchor", headers=legal_headers
        )
        read_response = await client.get(
            f"/api/evidence-packages/{package_id}/anchor", headers=legal_headers
        )

        assert submit_response.status_code == 403, submit_response.text
        assert read_response.status_code == 200, read_response.text


class _UnreachableProvider:
    """A provider whose `submit_hash` must never run -- used to prove the race loser is
    stopped by the unique constraint before it can reach a (possibly billable) provider
    call."""

    provider_name = "transparency_log"

    async def submit_hash(self, evidence_hash: str) -> str:
        raise AssertionError("must not be reached: the race loser must never call the provider")

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        raise AssertionError("must not be reached")

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        raise AssertionError("must not be reached")


async def test_a_concurrent_submission_hits_the_unique_constraint_not_the_provider_twice(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QA review (2026-10-07): true concurrency can't be reproduced against SQLite (same
    limitation noted throughout this codebase's other concurrency tests) -- this forces the
    exact interleaving two simultaneous callers would produce by making the up-front
    existence check see nothing (as it would if a second caller's SELECT ran before the
    first caller's INSERT committed), so the only thing standing between two submissions is
    `uq_blockchain_anchors_one_per_package` itself. For Constellation, a second real
    submission would be a real, billable API call the loser of this race must never make --
    `_UnreachableProvider` asserts that directly."""
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-race@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    organization_id = await _organization_id_for_package(db_session_factory, package_id)

    async with db_session_factory() as session:
        # The real first submission, committed -- what caller A already succeeded at.
        BlockchainAnchorRepository(session).add(
            BlockchainAnchor(
                organization_id=organization_id,
                evidence_package_id=package_id,
                provider="transparency_log",
                anchor_ref="ref-0",
                status=AnchorStatus.CONFIRMED.value,
            )
        )
        await session.commit()

    async def _sees_nothing(
        self: BlockchainAnchorRepository, *args: object, **kwargs: object
    ) -> None:
        return None

    # Caller B: its own up-front check is forced to see nothing (the race), so it proceeds
    # straight to the placeholder insert, which must fail on the constraint instead.
    monkeypatch.setattr(
        BlockchainAnchorRepository, "get_by_package_and_organization", _sees_nothing
    )

    async with db_session_factory() as session:
        with pytest.raises(AnchorAlreadySubmittedError):
            await anchoring_service.submit_anchor(
                session,
                organization_id=organization_id,
                evidence_package_id=package_id,
                actor_id=None,
                provider=_UnreachableProvider(),
            )


async def test_recheck_resolves_the_anchor_s_own_provider_not_the_current_default(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: `check_anchor_status` used to call `get_provider()` (the CURRENT default),
    not the adapter this specific anchor was actually submitted through. Forces the exact
    scenario that would break: the anchor is `transparency_log`, but the default has since
    been flipped to `constellation` (with no real credentials configured) -- a recheck must
    still resolve and use the transparency log, never attempt to build the Constellation
    adapter at all."""
    headers, package_id = await _package_id_for_simple_approval(
        client,
        email="anchor-provider-switch@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    submitted = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    anchor_id = submitted.json()["id"]
    assert submitted.json()["provider"] == "transparency_log"

    settings = get_settings()
    monkeypatch.setattr(settings, "anchoring_provider", "constellation_digital_evidence")
    # No constellation_ded_* settings are configured -- if check_anchor_status ever again
    # resolved the CURRENT default instead of this anchor's own provider, this call would
    # raise AnchoringProviderError("...missing settings...") instead of succeeding.

    response = await client.post(f"/api/blockchain-anchors/{anchor_id}/recheck", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["provider"] == "transparency_log"
