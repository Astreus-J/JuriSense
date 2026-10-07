"""FEATURE-8.3 (STORY-8.3.1, ADR-007): the public, unauthenticated verification endpoint
(`GET /api/public/verify`). Exercised against the real default `AnchoringProvider`
(`transparency_log`), same "no network, no mocking the provider itself" discipline as
`test_blockchain_anchor.py`.
"""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.evidence.application import verification_service
from app.evidence.domain.anchoring import AnchorProof, AnchorStatus
from app.evidence.domain.errors import AnchoringProviderError
from app.evidence.infrastructure.models import BlockchainAnchor, EvidencePackage
from app.evidence.infrastructure.repositories import BlockchainAnchorRepository
from tests.approvals.conftest import register_org_and_login
from tests.evidence.test_blockchain_anchor import _package_id_for_simple_approval


async def _package_merkle_root(
    db_session_factory: async_sessionmaker, package_id: uuid.UUID
) -> str:
    async with db_session_factory() as session:
        return (await session.get(EvidencePackage, package_id)).merkle_root


async def _package_decision_id(
    db_session_factory: async_sessionmaker, package_id: uuid.UUID
) -> uuid.UUID:
    async with db_session_factory() as session:
        return (await session.get(EvidencePackage, package_id)).decision_id


async def _anchored_package(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    *,
    email: str,
    mock_openrouter,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Returns (decision_id, package_id, merkle_root) for a package with a confirmed anchor."""
    headers, package_id = await _package_id_for_simple_approval(
        client, email=email, mock_openrouter=mock_openrouter, db_session_factory=db_session_factory
    )
    submitted = await client.post(f"/api/evidence-packages/{package_id}/anchor", headers=headers)
    assert submitted.status_code == 201, submitted.text

    decision_id = await _package_decision_id(db_session_factory, package_id)
    merkle_root = await _package_merkle_root(db_session_factory, package_id)
    return decision_id, package_id, merkle_root


async def test_verify_by_hash_returns_verified(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    _, _, merkle_root = await _anchored_package(
        client, db_session_factory, email="verify-hash@example.com", mock_openrouter=mock_openrouter
    )

    response = await client.get(f"/api/public/verify?ref={merkle_root}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "verified"
    assert body["evidence_hash"] == merkle_root
    assert body["provider"] == "transparency_log"
    assert body["confirmed_at"] is not None


async def test_verify_by_decision_id_returns_verified(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    decision_id, _, merkle_root = await _anchored_package(
        client,
        db_session_factory,
        email="verify-decision@example.com",
        mock_openrouter=mock_openrouter,
    )

    response = await client.get(f"/api/public/verify?ref={decision_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "verified"
    assert body["evidence_hash"] == merkle_root


async def test_verify_requires_no_authentication(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """The defining property of this route: no Authorization header, no session cookie."""
    _, _, merkle_root = await _anchored_package(
        client,
        db_session_factory,
        email="verify-noauth@example.com",
        mock_openrouter=mock_openrouter,
    )

    response = await client.get(f"/api/public/verify?ref={merkle_root}", headers={})

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "verified"


async def test_verify_is_not_scoped_to_the_caller_s_organization(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """Deliberately global by design (docs/06-blockchain/verification.md) -- a visitor who
    knows org A's reference can check it while authenticated as org B, or with no
    authentication at all. This is the one documented, intentional exception to this
    product's otherwise non-negotiable tenant isolation (ADR-003)."""
    _, _, merkle_root = await _anchored_package(
        client,
        db_session_factory,
        email="verify-org-a@example.com",
        mock_openrouter=mock_openrouter,
    )
    org_b_headers = await register_org_and_login(client, "verify-org-b@example.com")

    response = await client.get(f"/api/public/verify?ref={merkle_root}", headers=org_b_headers)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "verified"


async def test_verify_returns_not_found_for_an_unknown_hash(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/public/verify?ref={'0' * 64}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "not_found"
    assert body["provider"] is None


async def test_verify_returns_not_found_for_an_unknown_decision_id(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(f"/api/public/verify?ref={uuid.uuid4()}")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "not_found"


async def test_verify_returns_not_found_for_a_garbage_reference(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/public/verify?ref=not-a-hash-or-a-uuid")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "not_found"


async def test_verify_returns_not_found_for_a_failed_anchor(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """QA review (2026-10-07): the `anchor.status == FAILED` branch had no test. A failed
    submission leaves nothing a visitor can trust, so it reads the same as "no anchor"."""
    _, package_id = await _package_id_for_simple_approval(
        client,
        email="verify-failed-anchor@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    merkle_root = await _package_merkle_root(db_session_factory, package_id)

    async with db_session_factory() as session:
        organization_id = (await session.get(EvidencePackage, package_id)).organization_id
        BlockchainAnchorRepository(session).add(
            BlockchainAnchor(
                organization_id=organization_id,
                evidence_package_id=package_id,
                provider="transparency_log",
                anchor_ref="never-settled",
                status=AnchorStatus.FAILED.value,
            )
        )
        await session.commit()

    response = await client.get(f"/api/public/verify?ref={merkle_root}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "not_found"
    assert body["evidence_hash"] == merkle_root


async def test_verify_returns_not_found_for_a_package_with_no_anchor_yet(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    _, package_id = await _package_id_for_simple_approval(
        client,
        email="verify-unanchored@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    merkle_root = await _package_merkle_root(db_session_factory, package_id)

    response = await client.get(f"/api/public/verify?ref={merkle_root}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "not_found"
    assert body["evidence_hash"] == merkle_root  # resolved the package, just nothing anchored


async def test_verify_returns_mismatch_when_the_stored_hash_changed_after_anchoring(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """Forces exactly the tamper this status exists to catch: the EvidencePackage row's
    merkle_root changes after a real anchor was already confirmed against the original value
    (mirrors test_evidence_package.py's identical "rewrite history" pattern)."""
    decision_id, package_id, _original_root = await _anchored_package(
        client,
        db_session_factory,
        email="verify-mismatch@example.com",
        mock_openrouter=mock_openrouter,
    )

    async with db_session_factory() as session:
        package = await session.get(EvidencePackage, package_id)
        package.merkle_root = "f" * 64
        await session.commit()

    response = await client.get(f"/api/public/verify?ref={decision_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "mismatch"
    assert body["evidence_hash"] == "f" * 64


class _SlowProvider:
    """Stands in for a chain that hasn't finalized yet -- the transparency log confirms
    synchronously, so "pending" can't be reached through the real HTTP flow; this proves the
    service's own handling of a provider that still reports `submitted`."""

    provider_name = "transparency_log"

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        return AnchorProof(
            status=AnchorStatus.SUBMITTED, confirmed_at=None, reference_url="https://example.com"
        )

    async def submit_hash(self, evidence_hash: str) -> str:
        raise AssertionError("not used in this test")

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        raise AssertionError("must not be called while still pending")


async def test_verify_returns_pending_for_an_unconfirmed_anchor(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, package_id = await _package_id_for_simple_approval(
        client,
        email="verify-pending@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    merkle_root = await _package_merkle_root(db_session_factory, package_id)

    monkeypatch.setattr(verification_service, "get_provider_by_name", lambda name: _SlowProvider())

    async with db_session_factory() as session:
        organization_id = (await session.get(EvidencePackage, package_id)).organization_id
        BlockchainAnchorRepository(session).add(
            BlockchainAnchor(
                organization_id=organization_id,
                evidence_package_id=package_id,
                provider="transparency_log",
                anchor_ref="not-yet-settled",
                status=AnchorStatus.SUBMITTED.value,
            )
        )
        await session.commit()

    response = await client.get(f"/api/public/verify?ref={merkle_root}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["reference_url"] == "https://example.com"


class _BrokenProvider:
    """Stands in for a provider call that fails outright (a `git`/subprocess error, or a
    network error once Constellation is active)."""

    provider_name = "transparency_log"

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        raise AnchoringProviderError("simulated provider outage")

    async def submit_hash(self, evidence_hash: str) -> str:
        raise AssertionError("not used in this test")

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        raise AssertionError("must not be called when get_proof itself failed")


async def test_verify_returns_pending_not_a_500_when_the_provider_call_fails(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security review (2026-10-07): public_routes.py promises exactly one HTTP status (200)
    for every outcome -- a provider failure must degrade to `pending` in the body, never an
    unhandled 500, which would itself be the status-code side channel the design promises not
    to have."""
    _, package_id = await _package_id_for_simple_approval(
        client,
        email="verify-provider-outage@example.com",
        mock_openrouter=mock_openrouter,
        db_session_factory=db_session_factory,
    )
    merkle_root = await _package_merkle_root(db_session_factory, package_id)

    monkeypatch.setattr(
        verification_service, "get_provider_by_name", lambda name: _BrokenProvider()
    )

    async with db_session_factory() as session:
        organization_id = (await session.get(EvidencePackage, package_id)).organization_id
        BlockchainAnchorRepository(session).add(
            BlockchainAnchor(
                organization_id=organization_id,
                evidence_package_id=package_id,
                provider="transparency_log",
                anchor_ref="whatever",
                status=AnchorStatus.SUBMITTED.value,
            )
        )
        await session.commit()

    response = await client.get(f"/api/public/verify?ref={merkle_root}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["provider"] is None
