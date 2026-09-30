import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.db import SessionDep
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User
from app.policies.api.schemas import (
    AggregatePreviewResponse,
    ComplianceReviewDetailResponse,
    ComplianceReviewResponse,
    ContractSimulationResultResponse,
    CreatePolicyRequest,
    CreatePolicyResponse,
    CreateRuleRequest,
    PolicyResponse,
    PolicyVersionResponse,
    RiskResponse,
    RuleEvaluationRecordResponse,
    RuleEvaluationResponse,
    RuleResponse,
    SimulateRequest,
    SimulationResponse,
    TriggerReviewRequest,
)
from app.policies.application import (
    compliance_review_service,
    policy_service,
    publish_service,
    rule_service,
)
from app.policies.application.simulation_service import run_simulation
from app.policies.domain.errors import (
    ComplianceReviewNotFoundError,
    ContractVersionNotFoundError,
    DuplicateRuleKeyError,
    NoDraftVersionToPublishError,
    PolicyNotFoundError,
    PolicyVersionNotDraftError,
    PolicyVersionNotFoundError,
    RuleNotFoundError,
    RuleValidationError,
)

router = APIRouter(prefix="/policies", tags=["policies"])
compliance_router = APIRouter(prefix="/compliance", tags=["compliance"])

CanCreatePolicies = Annotated[User, Depends(require_permission(Module.POLICIES, "create"))]
CanReadPolicies = Annotated[User, Depends(require_permission(Module.POLICIES, "read"))]
CanUpdatePolicies = Annotated[User, Depends(require_permission(Module.POLICIES, "update"))]

CanCreateComplianceReviews = Annotated[
    User, Depends(require_permission(Module.COMPLIANCE_REVIEWS, "create"))
]
CanReadComplianceReviews = Annotated[
    User, Depends(require_permission(Module.COMPLIANCE_REVIEWS, "read"))
]


@router.post("", response_model=CreatePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: CreatePolicyRequest, user: CanCreatePolicies, session: SessionDep
) -> CreatePolicyResponse:
    policy, version = await policy_service.create_policy(
        session, organization_id=user.organization_id, actor_id=user.id, name=body.name
    )
    return CreatePolicyResponse(
        policy=PolicyResponse.model_validate(policy),
        initial_version=PolicyVersionResponse.model_validate(version),
    )


@router.get("", response_model=list[PolicyResponse])
async def list_policies(user: CanReadPolicies, session: SessionDep) -> list[PolicyResponse]:
    policies = await policy_service.list_policies(session, organization_id=user.organization_id)
    return [PolicyResponse.model_validate(p) for p in policies]


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID, user: CanReadPolicies, session: SessionDep
) -> PolicyResponse:
    try:
        policy = await policy_service.get_policy(
            session, organization_id=user.organization_id, policy_id=policy_id
        )
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return PolicyResponse.model_validate(policy)


@router.get("/{policy_id}/versions", response_model=list[PolicyVersionResponse])
async def list_versions(
    policy_id: uuid.UUID, user: CanReadPolicies, session: SessionDep
) -> list[PolicyVersionResponse]:
    try:
        versions = await policy_service.list_versions(
            session, organization_id=user.organization_id, policy_id=policy_id
        )
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return [PolicyVersionResponse.model_validate(v) for v in versions]


@router.post(
    "/{policy_id}/versions",
    response_model=PolicyVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft_version(
    policy_id: uuid.UUID, user: CanCreatePolicies, session: SessionDep
) -> PolicyVersionResponse:
    """BR-POL-001's copy-modify path: a new draft version, its rules copied from the
    current published version (if any)."""
    try:
        version = await policy_service.create_draft_version(
            session, organization_id=user.organization_id, actor_id=user.id, policy_id=policy_id
        )
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return PolicyVersionResponse.model_validate(version)


@router.get("/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse)
async def get_version(
    policy_id: uuid.UUID, version_id: uuid.UUID, user: CanReadPolicies, session: SessionDep
) -> PolicyVersionResponse:
    try:
        version = await policy_service.get_version(
            session,
            organization_id=user.organization_id,
            policy_id=policy_id,
            version_id=version_id,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return PolicyVersionResponse.model_validate(version)


@router.post("/{policy_id}/versions/{version_id}/publish", response_model=PolicyVersionResponse)
async def publish_version(
    policy_id: uuid.UUID, version_id: uuid.UUID, user: CanUpdatePolicies, session: SessionDep
) -> PolicyVersionResponse:
    """#58: freezes every Rule in this version (BR-POL-001) and makes it the Policy's one
    current version (BR-POL-002)."""
    try:
        version = await publish_service.publish_version(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            policy_id=policy_id,
            version_id=version_id,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except NoDraftVersionToPublishError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return PolicyVersionResponse.model_validate(version)


@router.post(
    "/{policy_id}/versions/{version_id}/rules",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: CreateRuleRequest,
    user: CanCreatePolicies,
    session: SessionDep,
) -> RuleResponse:
    try:
        rule = await rule_service.create_rule(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            policy_id=policy_id,
            version_id=version_id,
            rule_yaml=body.yaml,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except PolicyVersionNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except DuplicateRuleKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except RuleValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    return RuleResponse.model_validate(rule)


@router.get("/{policy_id}/versions/{version_id}/rules", response_model=list[RuleResponse])
async def list_rules(
    policy_id: uuid.UUID, version_id: uuid.UUID, user: CanReadPolicies, session: SessionDep
) -> list[RuleResponse]:
    try:
        rules = await rule_service.list_rules(
            session,
            organization_id=user.organization_id,
            policy_id=policy_id,
            version_id=version_id,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return [RuleResponse.model_validate(r) for r in rules]


@router.get(
    "/{policy_id}/versions/{version_id}/rules/{rule_id}",
    response_model=RuleResponse,
)
async def get_rule(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: CanReadPolicies,
    session: SessionDep,
) -> RuleResponse:
    try:
        rule = await rule_service.get_rule(
            session,
            organization_id=user.organization_id,
            policy_id=policy_id,
            version_id=version_id,
            rule_id=rule_id,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError, RuleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return RuleResponse.model_validate(rule)


@router.put(
    "/{policy_id}/versions/{version_id}/rules/{rule_id}",
    response_model=RuleResponse,
)
async def update_rule(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: CreateRuleRequest,
    user: CanUpdatePolicies,
    session: SessionDep,
) -> RuleResponse:
    try:
        rule = await rule_service.update_rule(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            policy_id=policy_id,
            version_id=version_id,
            rule_id=rule_id,
            rule_yaml=body.yaml,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError, RuleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except PolicyVersionNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except DuplicateRuleKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except RuleValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    return RuleResponse.model_validate(rule)


@router.post("/{policy_id}/versions/{version_id}/simulate", response_model=SimulationResponse)
async def simulate(
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: SimulateRequest,
    user: CanReadPolicies,
    session: SessionDep,
) -> SimulationResponse:
    """#61: dry-run against one or more existing `ContractVersion`s. No `ComplianceReview`
    /`RuleEvaluation`/`Decision` row is created and no real domain event is emitted --
    see `app.policies.application.simulation_service`'s module docstring for the scope
    call this endpoint implements."""
    try:
        result = await run_simulation(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            policy_id=policy_id,
            version_id=version_id,
            contract_version_ids=body.contract_version_ids,
        )
    except (PolicyNotFoundError, PolicyVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return SimulationResponse(
        policy_id=result.policy_id,
        policy_version_id=result.policy_version_id,
        version_number=result.version_number,
        version_status=result.version_status,
        contract_results=[
            ContractSimulationResultResponse(
                contract_version_id=cr.contract_version_id,
                rule_evaluations=[
                    RuleEvaluationResponse(
                        rule_id=re.rule_id,
                        rule_key=re.rule_key,
                        rule_name=re.rule_name,
                        outcome=re.outcome,
                        severity=re.severity,
                        approver_role=re.approver_role,
                        rationale=re.rationale,
                    )
                    for re in cr.rule_evaluations
                ],
                aggregate=AggregatePreviewResponse(
                    status=cr.aggregate.status,
                    required_approver_roles=list(cr.aggregate.required_approver_roles),
                ),
            )
            for cr in result.contract_results
        ],
    )


@compliance_router.post(
    "/reviews", response_model=ComplianceReviewResponse, status_code=status.HTTP_201_CREATED
)
async def trigger_review(
    body: TriggerReviewRequest, user: CanCreateComplianceReviews, session: SessionDep
) -> ComplianceReviewResponse:
    """#123: triggers a real `ComplianceReview` -- pools every currently-published
    `PolicyVersion` in the caller's organization (see
    `app.policies.application.compliance_review_service`'s module docstring for the
    multi-policy pooling design decision) and evaluates them against the given
    `ContractVersion`'s normalized evidence, persisting the result."""
    try:
        review = await compliance_review_service.trigger_review(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            contract_version_id=body.contract_version_id,
        )
    except ContractVersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return ComplianceReviewResponse.model_validate(review)


@compliance_router.get("/reviews/{review_id}", response_model=ComplianceReviewDetailResponse)
async def get_review(
    review_id: uuid.UUID, user: CanReadComplianceReviews, session: SessionDep
) -> ComplianceReviewDetailResponse:
    """The read-model #127/#62's frontend results screen needs: one `ComplianceReview`
    with its full `RuleEvaluation` and `Risk` lists."""
    try:
        review, evaluations, risks = await compliance_review_service.get_review_detail(
            session, organization_id=user.organization_id, review_id=review_id
        )
    except ComplianceReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return ComplianceReviewDetailResponse(
        review=ComplianceReviewResponse.model_validate(review),
        rule_evaluations=[RuleEvaluationRecordResponse.model_validate(e) for e in evaluations],
        risks=[RiskResponse.model_validate(r) for r in risks],
    )
