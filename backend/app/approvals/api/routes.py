import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.approvals.api.schemas import (
    ApprovalRequestResponse,
    ApproveRequestBody,
    DecisionResponse,
    OverrideDecisionRequest,
    RejectRequestBody,
)
from app.approvals.application import approval_service, decision_service
from app.approvals.domain.errors import (
    ApprovalRequestAlreadyResolvedError,
    ApprovalRequestNotFoundError,
    ApproverRoleMismatchError,
    DecisionAlreadyExistsError,
    DecisionNotEffectiveError,
    DecisionNotFoundError,
    EmptyJustificationError,
    OverriddenDecisionSupersessionError,
)
from app.core.db import SessionDep
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User

# Sanctioned cross-context read: the one way Approvals & Decisions confirms a caller-
# supplied `compliance_review_id` actually belongs to the caller's organization before
# listing its ApprovalRequests -- mirrors every other context's "check ownership before
# listing" discipline (e.g. compliance_review_service.list_reviews_for_contract_version's
# own check against Contracts & Documents). `get_review_detail` returns more than this
# route needs (the full RuleEvaluation/Risk lists too) -- reused as-is anyway, per this
# epic's own instruction not to reinvent that lookup; see
# tests/approvals/test_boundary_rules.py for the allowlisted surface this implies.
from app.policies.application.compliance_review_service import get_review_detail
from app.policies.domain.errors import ComplianceReviewNotFoundError

router = APIRouter(prefix="/approvals", tags=["approvals"])
decisions_router = APIRouter(prefix="/decisions", tags=["decisions"])

CanReadApprovals = Annotated[User, Depends(require_permission(Module.APPROVALS, "read"))]
CanUpdateApprovals = Annotated[User, Depends(require_permission(Module.APPROVALS, "update"))]


@router.get("/requests/pending", response_model=list[ApprovalRequestResponse])
async def list_pending_requests(
    user: CanReadApprovals, session: SessionDep
) -> list[ApprovalRequestResponse]:
    """The `/approvals` screen's inbox: this caller's own pending requests, across every
    review. Declared before `/requests/{request_id}` and `/requests` below -- FastAPI/
    Starlette matches routes in registration order, so this must come first or a request
    to `/requests/pending` would instead match `/requests/{request_id}` with
    `request_id="pending"` and fail UUID parsing."""
    requests = await approval_service.list_pending_for_actor(
        session, organization_id=user.organization_id, user_id=user.id
    )
    return [ApprovalRequestResponse.model_validate(r) for r in requests]


@router.post("/requests/{request_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    request_id: uuid.UUID, body: ApproveRequestBody, user: CanUpdateApprovals, session: SessionDep
) -> ApprovalRequestResponse:
    try:
        request = await approval_service.approve_request(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            request_id=request_id,
            justification=body.justification,
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ApprovalRequestAlreadyResolvedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ApproverRoleMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    except DecisionAlreadyExistsError as exc:
        # QA/security review (2026-10-01): defense-in-depth backstop, should be
        # effectively unreachable given resolve_if_pending's atomic UPDATE -- see that
        # error's own docstring.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except OverriddenDecisionSupersessionError as exc:
        # F1: an automatic re-evaluation chain may not replace a human's override (BR-DEC-003).
        # Nothing was written; the request stays pending for a human to resolve by manual review.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return ApprovalRequestResponse.model_validate(request)


@router.post("/requests/{request_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    request_id: uuid.UUID, body: RejectRequestBody, user: CanUpdateApprovals, session: SessionDep
) -> ApprovalRequestResponse:
    try:
        request = await approval_service.reject_request(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            request_id=request_id,
            justification=body.justification,
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ApprovalRequestAlreadyResolvedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except ApproverRoleMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    except EmptyJustificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    except DecisionAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except OverriddenDecisionSupersessionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return ApprovalRequestResponse.model_validate(request)


@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_request(
    request_id: uuid.UUID, user: CanReadApprovals, session: SessionDep
) -> ApprovalRequestResponse:
    try:
        request = await approval_service.get_request(
            session, organization_id=user.organization_id, request_id=request_id
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return ApprovalRequestResponse.model_validate(request)


@router.get("/requests", response_model=list[ApprovalRequestResponse])
async def list_requests(
    compliance_review_id: uuid.UUID, user: CanReadApprovals, session: SessionDep
) -> list[ApprovalRequestResponse]:
    """Mirrors `app.policies.api.routes.list_reviews`'s "check ownership before listing"
    pattern: a `compliance_review_id` that doesn't exist, or belongs to another
    organization, 404s -- it never comes back as a silently-empty list."""
    try:
        await get_review_detail(
            session, organization_id=user.organization_id, review_id=compliance_review_id
        )
    except ComplianceReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    requests = await approval_service.list_requests_for_review(
        session, organization_id=user.organization_id, compliance_review_id=compliance_review_id
    )
    return [ApprovalRequestResponse.model_validate(r) for r in requests]


@decisions_router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: uuid.UUID, user: CanReadApprovals, session: SessionDep
) -> DecisionResponse:
    try:
        decision = await decision_service.get_decision(
            session, organization_id=user.organization_id, decision_id=decision_id
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return DecisionResponse.model_validate(decision)


@decisions_router.post("/{decision_id}/override", response_model=DecisionResponse)
async def override_decision(
    decision_id: uuid.UUID,
    body: OverrideDecisionRequest,
    user: CanUpdateApprovals,
    session: SessionDep,
) -> DecisionResponse:
    """DEC-002/BR-DEC-003. RBAC: gated on `update` (same as approve/reject) rather than a
    new, narrower permission dimension -- the epic brief explicitly calls for reusing the
    existing grid's `RU`-holding roles as a loose match for "authorized Approver" rather
    than inventing a new permission axis for this one action."""
    try:
        decision = await decision_service.override_decision(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            decision_id=decision_id,
            new_status=body.new_status,
            justification=body.justification,
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except DecisionNotEffectiveError as exc:
        # F1: only the effective (ACTIVE) Decision is overridable; a SUPERSEDED one is historical.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except EmptyJustificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    return DecisionResponse.model_validate(decision)
