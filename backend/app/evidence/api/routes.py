import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import SessionDep
from app.evidence.api.schemas import (
    BlockchainAnchorResponse,
    DecisionPassportResponse,
    EvidencePackageResponse,
    RecomputeResponse,
)
from app.evidence.application import (
    anchoring_service,
    decision_passport_service,
    evidence_package_service,
)
from app.evidence.application.evidence_package_service import PackageView
from app.evidence.domain.errors import (
    AnchorAlreadySubmittedError,
    AnchoringProviderError,
    BlockchainAnchorNotFoundError,
    EvidenceError,
    EvidencePackageNotFoundError,
)
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User

logger = logging.getLogger("jurisense.evidence.api")

router = APIRouter(prefix="/evidence-packages", tags=["evidence"])
decision_passport_router = APIRouter(prefix="/decisions", tags=["evidence"])
blockchain_anchor_router = APIRouter(prefix="/blockchain-anchors", tags=["evidence"])

CanReadEvidence = Annotated[User, Depends(require_permission(Module.EVIDENCE, "read"))]
# FEATURE-8.2 (2026-10-07): submitting for anchoring is gated on the "update" permission --
# under today's DEFAULT_ROLE_GRID (backend/app/identity/domain/rbac.py) that is ADMIN-only,
# since every other role's Evidence grant is read-only. Deliberately the narrowest default
# for a new, externally-facing, costs-a-real-request action; widening it to
# COMPLIANCE/LEGAL is a product call for the user, not made here.
CanUpdateEvidence = Annotated[User, Depends(require_permission(Module.EVIDENCE, "update"))]


def _to_response(view: PackageView) -> EvidencePackageResponse:
    return EvidencePackageResponse(
        id=view.package.id,
        organization_id=view.package.organization_id,
        decision_id=view.package.decision_id,
        merkle_root=view.package.merkle_root,
        evidence_count=view.package.evidence_count,
        created_at=view.package.created_at,
        evidence=[
            {
                "id": row.id,
                "type": row.type,
                "ref_id": row.ref_id,
                "payload": row.payload,
                "content_hash": row.content_hash,
            }
            for row in view.evidence
        ],
        override_addenda=[
            {
                "id": addendum.id,
                "evidence_package_id": addendum.evidence_package_id,
                "decision_id": addendum.decision_id,
                "sequence_number": addendum.sequence_number,
                "original_status": addendum.original_status,
                "new_status": addendum.new_status,
                "justification": addendum.justification,
                "overridden_by": addendum.overridden_by,
                "overridden_at": addendum.overridden_at,
                "previous_hash": addendum.previous_hash,
                "content_hash": addendum.content_hash,
            }
            for addendum in view.override_addenda
        ],
    )


@router.get("/{package_id}", response_model=EvidencePackageResponse)
async def get_package(
    package_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> EvidencePackageResponse:
    try:
        view = await evidence_package_service.get_package(
            session, organization_id=user.organization_id, package_id=package_id
        )
    except EvidencePackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return _to_response(view)


@router.post("/{package_id}/recompute", response_model=RecomputeResponse)
async def recompute_package(
    package_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> RecomputeResponse:
    """BR-EVD-001: recomputes the Merkle root from the persisted Evidence rows. Read-only, so it
    requires only the read permission. The stored root is never overwritten."""
    try:
        result = await evidence_package_service.recompute(
            session, organization_id=user.organization_id, package_id=package_id
        )
    except EvidencePackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return RecomputeResponse(
        evidence_package_id=result.evidence_package_id,
        stored_merkle_root=result.stored_merkle_root,
        recomputed_merkle_root=result.recomputed_merkle_root,
        matches=result.matches,
        evidence_count=result.evidence_count,
        mismatched_evidence_ids=list(result.mismatched_evidence_ids),
    )


@decision_passport_router.get(
    "/{decision_id}/evidence-package", response_model=EvidencePackageResponse
)
async def get_decision_package(
    decision_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> EvidencePackageResponse:
    """The Decision Passport for one Decision. A Decision in another organization, and a
    Decision with no package, both return 404: the two are indistinguishable by design."""
    try:
        view = await evidence_package_service.get_package_for_decision(
            session, organization_id=user.organization_id, decision_id=decision_id
        )
    except EvidencePackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return _to_response(view)


@decision_passport_router.get("/{decision_id}/passport", response_model=DecisionPassportResponse)
async def get_decision_passport(
    decision_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> DecisionPassportResponse:
    """STORY-7.3.1: the human-readable "why was this approved?" narrative for one Decision.
    Same 404 contract as `get_decision_package` above: a missing Decision, one in another
    organization, and one with no EvidencePackage yet are all indistinguishable (ADR-003).

    Security review (2026-10-06): catches `EvidenceError`, not just its
    `EvidencePackageNotFoundError` subclass. `decision_passport_service.get_decision_passport`
    also raises the base `EvidenceError` for a handful of "should be unreachable" broken-
    reference cases (its own Decision pointing at a review/contract version/supplier that no
    longer resolves) -- today genuinely unreachable (no archival/soft-delete path exists yet
    for any of those), but catching only the subclass would let a future one escape as an
    unhandled 500 instead of this route's documented 404, the same ADR-003 guarantee every
    other branch here already keeps."""
    try:
        passport = await decision_passport_service.get_decision_passport(
            session, organization_id=user.organization_id, decision_id=decision_id
        )
    except EvidenceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return DecisionPassportResponse.model_validate(passport)


@router.post("/{package_id}/anchor", response_model=BlockchainAnchorResponse, status_code=201)
async def submit_anchor(
    package_id: uuid.UUID, user: CanUpdateEvidence, session: SessionDep
) -> BlockchainAnchorResponse:
    """FEATURE-8.1/8.2 (ADR-007): submits this package's `merkle_root` for anchoring via the
    configured `AnchoringProvider`. One anchor per package -- a second call for an
    already-submitted package is a 409, not a silent duplicate."""
    try:
        result = await anchoring_service.submit_anchor(
            session,
            organization_id=user.organization_id,
            evidence_package_id=package_id,
            actor_id=user.id,
        )
    except EvidencePackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except AnchorAlreadySubmittedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except AnchoringProviderError as exc:
        # Security review (2026-10-07): exc.message can carry a third party's raw response
        # body or local git stderr -- logged for an operator to read, never echoed to the
        # caller (who, by definition, already holds this package's update permission, so
        # this is not a cross-tenant concern, just unnecessary detail in an HTTP response).
        logger.warning("Anchor submission failed for package %s: %s", package_id, exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The anchoring provider could not be reached. Try again shortly.",
        ) from exc
    return BlockchainAnchorResponse.model_validate(result.anchor)


@router.get("/{package_id}/anchor", response_model=BlockchainAnchorResponse | None)
async def get_package_anchor(
    package_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> BlockchainAnchorResponse | None:
    """`null` (not a 404) when the package exists but has not been submitted for anchoring
    yet -- a legitimate, common state distinct from the package itself not existing."""
    try:
        await evidence_package_service.get_package(
            session, organization_id=user.organization_id, package_id=package_id
        )
    except EvidencePackageNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    anchor = await anchoring_service.get_anchor_for_package(
        session, organization_id=user.organization_id, evidence_package_id=package_id
    )
    return BlockchainAnchorResponse.model_validate(anchor) if anchor else None


@blockchain_anchor_router.post("/{anchor_id}/recheck", response_model=BlockchainAnchorResponse)
async def recheck_anchor(
    anchor_id: uuid.UUID, user: CanReadEvidence, session: SessionDep
) -> BlockchainAnchorResponse:
    """Re-polls the provider for a `submitted` anchor's current state. Read-only from the
    caller's point of view (no new submission), so it requires only the read permission --
    mirrors `recompute_package`'s identical rationale."""
    try:
        result = await anchoring_service.check_anchor_status(
            session, organization_id=user.organization_id, anchor_id=anchor_id
        )
    except BlockchainAnchorNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except AnchoringProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
    return BlockchainAnchorResponse.model_validate(result.anchor)
