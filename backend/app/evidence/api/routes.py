import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import SessionDep
from app.evidence.api.schemas import EvidencePackageResponse, RecomputeResponse
from app.evidence.application import evidence_package_service
from app.evidence.application.evidence_package_service import PackageView
from app.evidence.domain.errors import EvidencePackageNotFoundError
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User

router = APIRouter(prefix="/evidence-packages", tags=["evidence"])
decision_passport_router = APIRouter(prefix="/decisions", tags=["evidence"])

CanReadEvidence = Annotated[User, Depends(require_permission(Module.EVIDENCE, "read"))]


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
