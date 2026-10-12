"""Trigger flow for a real `ComplianceReview` (#123/#125/#126; ADR-010;
docs/03-domain/domain-model.md "ComplianceReview"/"RuleEvaluation"/"Risk").

Mirrors `simulation_service.run_simulation`'s exact pattern (see that module's own
docstring for the two documented differences): this resolves every currently-published
`PolicyVersion` in the organization automatically rather than taking an explicit
`version_id` (see "Design decision: multi-policy pooling" below, and
`app.policies.infrastructure.models.ComplianceReview`'s own docstring), and it persists
real `ComplianceReview`/`RuleEvaluation`/`Risk` rows and emits real
`compliance.review_started`/`compliance.rule_evaluated`/`compliance.review_completed`
audit events -- simulation deliberately does neither.

## Design decision: multi-policy pooling (#123 -- resolving an open question)
`docs/03-domain/domain-model.md`'s `Policy` entity states no one-org-one-active-policy
constraint anywhere, so an organization may have several independently-published Policies
active at once (e.g. a "Vendor Compliance" policy and a separate "Data Privacy" policy).
Rather than force a policy-selection step onto the triggering user -- which would let a
reviewer silently skip one of them -- `trigger_review` pools the Rules of EVERY
currently-published `PolicyVersion` in the organization into one `ComplianceReview`: one
explainable APPROVE/REVIEW/BLOCK gate per contract, matching ADR-010's own framing that
the aggregation algorithm must be "simple enough to explain to a customer's Legal/
Compliance team in one sentence." The aggregation itself (`evaluation_service.
aggregate_preview`) is already order-independent (ADR-010 §2/BR-CMP-002), so pooling rules
from multiple policies into one aggregation pass is a straightforward extension, not a new
algorithm.

## Design decision: Risk provenance (#125 -- resolving an open question)
`Risk` "may or may not map 1:1" to a `RuleEvaluation` per domain-model.md. This epic's only
risk source is rule evaluation itself, so exactly one `Risk` row is derived per
`RuleEvaluation` whose outcome is `REVIEW` or `BLOCK` -- see
`app.policies.infrastructure.models.Risk`'s docstring for the full rationale and why the
schema doesn't hard-code 1:1.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application.approval_service import create_approval_requests_for_review
from app.approvals.application.decision_service import (
    create_decision_for_review,
    get_decision,
)
from app.contracts.application.evidence_service import (
    contract_version_belongs_to_organization,
    get_evidence_refs_for_contract_version,
    get_newer_analyzed_contract_version_id,
    get_supplier_id_for_contract_version,
)
from app.evidence.application.anchoring_service import enqueue_anchor_submission
from app.evidence.application.audit_service import emit_audit_event
from app.policies.application.context_builder import build_context_for_contract_version
from app.policies.application.evaluation_service import (
    AggregatePreview,
    RuleEvaluationResult,
    aggregate_preview,
    evaluate_policy_version,
)
from app.policies.domain.constants import (
    SEVERITY_ORDER,
    ComplianceReviewStatus,
    RuleOutcome,
    Severity,
)
from app.policies.domain.errors import ComplianceReviewNotFoundError, ContractVersionNotFoundError
from app.policies.domain.rule_dsl import referenced_paths_of
from app.policies.infrastructure.models import ComplianceReview, Risk, Rule, RuleEvaluation
from app.policies.infrastructure.repositories import (
    ComplianceReviewRepository,
    PolicyExceptionRepository,
    PolicyVersionRepository,
    RiskRepository,
    RuleEvaluationRepository,
    RuleRepository,
)
from app.suppliers.application.evidence_service import get_evidence_ref_for_supplier

logger = logging.getLogger("jurisense.policies.compliance_review")

# RuleEvaluation outcomes that represent an actual finding, per the Risk-provenance
# design decision above -- PASS/NOT_APPLICABLE represent the absence of one.
_RISK_OUTCOMES = frozenset({RuleOutcome.REVIEW.value, RuleOutcome.BLOCK.value})


def _build_evidence_refs(
    rule: Rule,
    *,
    contract_version_id: uuid.UUID,
    contract_evidence_refs: dict[str, dict[str, Any]],
    supplier_evidence_ref: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Maps a rule's referenced evaluation-context paths (`rule_dsl.referenced_paths_of`)
    back to the concrete evidence that produced them -- the mechanism behind the
    product's "WHY, EVIDENCE, POLICY, SOURCE" explainability principle (#126). A
    `contract.*` path resolves to the extracted field's provenance (document_id/page/
    text_span); a `supplier.*` path resolves to the current `SupplierProfile`'s
    identifying ids. A path with no available evidence (e.g. the field was never
    extracted) is simply omitted -- consistent with that same rule evaluating to
    `NOT_APPLICABLE` rather than a misleading reference to nothing."""
    refs: list[dict[str, Any]] = []
    for path in referenced_paths_of(rule.when):
        if path.startswith("contract."):
            provenance = contract_evidence_refs.get(path)
            if provenance is not None:
                refs.append(
                    {
                        "context_path": path,
                        "source": "contract_extracted_field",
                        "contract_version_id": str(contract_version_id),
                        "document_id": provenance.get("document_id"),
                        "page": provenance.get("page"),
                        "text_span": provenance.get("text_span"),
                    }
                )
        elif path.startswith("supplier."):
            if supplier_evidence_ref is not None:
                refs.append(
                    {"context_path": path, "source": "supplier_profile", **supplier_evidence_ref}
                )
    return refs


async def trigger_review(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    contract_version_id: uuid.UUID,
) -> ComplianceReview:
    """#123: resolves every currently-published `PolicyVersion` in the organization,
    pools their Rules, evaluates them against the given `ContractVersion`'s normalized
    evidence (#60/#61's already-tested engine, reused verbatim), and persists the result
    as one immutable `ComplianceReview` + its `RuleEvaluation`/`Risk` rows.

    Commits itself -- the entry use case for `POST /compliance/reviews`. Re-evaluation
    (FEATURE-6.4) calls `execute_review` directly instead, so it can make its own
    Decision-flag update and this review commit as one unit.

    #199: if this review's outcome is APPROVE/BLOCK (a Decision -- and therefore an
    EvidencePackage -- was created for it), automatic anchor submission is enqueued right
    after the commit below, never before (see `enqueue_anchor_submission`'s own docstring
    for why that ordering is mandatory)."""
    outcome = await execute_review(
        session,
        organization_id=organization_id,
        actor_id=actor_id,
        contract_version_id=contract_version_id,
    )
    await session.commit()
    await session.refresh(outcome.review)
    if outcome.decision_id is not None:
        # QA review (2026-10-11): a failure here must never look like the review itself
        # failed -- the Decision above is already committed. Logged and swallowed; the
        # package stays anchorable manually (POST /evidence-packages/{id}/anchor) if this
        # automatic hand-off never reaches the worker.
        try:
            await enqueue_anchor_submission(
                decision_id=outcome.decision_id,
                organization_id=organization_id,
                actor_id=actor_id,
            )
        except Exception:
            logger.exception(
                "Could not enqueue automatic anchor submission for decision %s",
                outcome.decision_id,
            )
    return outcome.review


@dataclass(frozen=True)
class ReviewOutcome:
    """`execute_review`'s return shape (#199). `decision_id` is set only on the synchronous
    APPROVE/BLOCK path (a Decision -- and its EvidencePackage -- was created this call);
    `None` for REVIEW, whose Decision (if any) is created later from `approval_service`.
    Deliberately carries the id, not the `Decision` ORM object itself: Policy & Compliance
    may not import Approvals' infrastructure (`tests/policies/test_boundary_rules.py`)."""

    review: ComplianceReview
    decision_id: uuid.UUID | None


async def execute_review(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    contract_version_id: uuid.UUID,
    supersedes_decision_id: uuid.UUID | None = None,
) -> ReviewOutcome:
    """The `trigger_review` body, minus the commit: evaluates and persists one
    `ComplianceReview` (plus, for APPROVE/BLOCK, its `Decision`; for REVIEW, its approval
    chain's first step) in the caller's transaction. The caller owns commit.

    `actor_id` is `None` for system-initiated re-evaluation (the FEATURE-6.4 sweep has no
    human actor; audit events accept `actor_id=None`). `supersedes_decision_id` links a
    re-evaluation to the Decision it replaces (BR-DEC-002): it is stored on this review and
    copied onto the Decision the review produces -- on the synchronous APPROVE/BLOCK path
    here, and later, on the deferred path in `approval_service` for a REVIEW chain."""
    if not await contract_version_belongs_to_organization(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    ):
        raise ContractVersionNotFoundError()
    if supersedes_decision_id is not None:
        # Security review (2026-10-03): a supersedes link must never cross tenants (it would
        # silently suppress another organization's Decision from the staleness sweep forever).
        # get_decision is org-scoped and raises DecisionNotFoundError for a foreign id.
        await get_decision(
            session, organization_id=organization_id, decision_id=supersedes_decision_id
        )

    version_repo = PolicyVersionRepository(session)
    rule_repo = RuleRepository(session)
    policy_versions = await version_repo.list_current_by_organization(organization_id)

    rules: list[Rule] = []
    # #179: Risk.category alone (= rule_key) can't disambiguate two different Policies that
    # happen to reuse the same rule_key string -- rule_key is only unique PER PolicyVersion
    # (uq_rule_key_per_version), never across Policies. This map lets every Risk row also
    # carry the owning Policy's id.
    policy_id_by_version_id: dict[uuid.UUID, uuid.UUID] = {}
    for policy_version in policy_versions:
        rules.extend(await rule_repo.list_by_version(policy_version.id))
        policy_id_by_version_id[policy_version.id] = policy_version.policy_id

    context = await build_context_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )

    review = ComplianceReview(
        organization_id=organization_id,
        contract_version_id=contract_version_id,
        policy_version_ids=[str(pv.id) for pv in policy_versions],
        status=ComplianceReviewStatus.IN_PROGRESS.value,
        supersedes_decision_id=supersedes_decision_id,
    )
    ComplianceReviewRepository(session).add(review)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="compliance.review_started",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "compliance_review_id": str(review.id),
            "contract_version_id": str(contract_version_id),
            "policy_version_ids": review.policy_version_ids,
            "rule_count": len(rules),
        },
    )

    supplier_id = await get_supplier_id_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )
    # #120: every active PolicyException applicable to this review's own supplier/
    # contract-version target, keyed by rule_id so evaluate_policy_version can look each
    # pooled rule's up in O(1) without evaluation_service ever touching the repository.
    active_exceptions = await PolicyExceptionRepository(session).list_active_for_rule_ids(
        [rule.id for rule in rules],
        organization_id=organization_id,
        supplier_id=supplier_id,
        contract_version_id=contract_version_id,
        now=datetime.now(UTC),
    )
    active_exceptions_by_rule_id = {str(exc.rule_id): exc for exc in active_exceptions}

    results: list[RuleEvaluationResult] = evaluate_policy_version(
        rules, context, active_exceptions_by_rule_id=active_exceptions_by_rule_id
    )
    aggregate: AggregatePreview = aggregate_preview(results)

    contract_evidence_refs = await get_evidence_refs_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )
    supplier_evidence_ref: dict[str, Any] | None = None
    if supplier_id is not None:
        supplier_evidence_ref = await get_evidence_ref_for_supplier(
            session, organization_id=organization_id, supplier_id=supplier_id
        )

    rules_by_id = {str(rule.id): rule for rule in rules}
    eval_repo = RuleEvaluationRepository(session)
    risk_repo = RiskRepository(session)

    evaluations: list[RuleEvaluation] = []
    evaluation_evidence_refs: list[list[dict[str, Any]]] = []
    for result in results:
        rule = rules_by_id[result.rule_id]
        evidence_refs = _build_evidence_refs(
            rule,
            contract_version_id=contract_version_id,
            contract_evidence_refs=contract_evidence_refs,
            supplier_evidence_ref=supplier_evidence_ref,
        )
        evaluation = RuleEvaluation(
            compliance_review_id=review.id,
            rule_id=rule.id,
            rule_key=result.rule_key,
            rule_name=result.rule_name,
            outcome=result.outcome,
            severity=result.severity,
            approver_role=result.approver_role,
            rationale=result.rationale,
            evidence_refs=evidence_refs,
            exception_id=uuid.UUID(result.exception_id) if result.exception_id else None,
        )
        eval_repo.add(evaluation)
        evaluations.append(evaluation)
        evaluation_evidence_refs.append(evidence_refs)

    # One flush assigns every RuleEvaluation's generated id, needed both for the
    # per-evaluation audit event payload below and for Risk's evidence_refs mirror.
    await session.flush()

    for evaluation, result, evidence_refs in zip(
        evaluations, results, evaluation_evidence_refs, strict=True
    ):
        await emit_audit_event(
            session,
            event_type="compliance.rule_evaluated",
            actor_id=actor_id,
            organization_id=organization_id,
            payload={
                "compliance_review_id": str(review.id),
                "rule_evaluation_id": str(evaluation.id),
                "rule_id": result.rule_id,
                "rule_key": result.rule_key,
                "outcome": result.outcome,
                "severity": result.severity,
            },
        )
        if result.outcome in _RISK_OUTCOMES:
            rule = rules_by_id[result.rule_id]
            risk_repo.add(
                Risk(
                    compliance_review_id=review.id,
                    policy_id=policy_id_by_version_id[rule.policy_version_id],
                    category=result.rule_key,
                    description=result.rationale,
                    severity=result.severity,
                    evidence_refs=evidence_refs,
                )
            )

    review.status = aggregate.status
    review.completed_at = datetime.now(UTC)

    await emit_audit_event(
        session,
        event_type="compliance.review_completed",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "compliance_review_id": str(review.id),
            "status": aggregate.status,
            "required_approver_roles": list(aggregate.required_approver_roles),
            "rule_evaluation_count": len(results),
        },
    )

    # EPIC-6 (docs/03-domain/approvals.md): this codebase's first write-side (not
    # read-only "evidence port") cross-context call -- Policy & Compliance hands off this
    # review's aggregate outcome to Approvals & Decisions, in the SAME transaction, before
    # this function's own commit below. Only primitives cross the boundary (plain
    # uuid.UUID/str), never a Severity enum instance or any ORM object. A REVIEW outcome
    # routes to the workflow's first approval step (no Decision yet -- one is created
    # later, from inside approval_service.approve_request/reject_request, once the chain
    # reaches a terminal state); APPROVE/BLOCK need no human step at all, so their
    # Decision is created immediately, right here, alongside this call rather than
    # instead of it.
    decision_id: uuid.UUID | None = None
    if aggregate.status == RuleOutcome.REVIEW.value:
        # Same highest-triggered-REVIEW-severity tie-break `aggregate_preview` already
        # uses internally to pick required_approver_roles -- recomputed here (as a plain
        # str, not a Severity enum instance) because AggregatePreview only exposes the
        # roles, not the tier itself. review_results is guaranteed non-empty: aggregate
        # Preview only returns REVIEW when at least one REVIEW-outcome result exists.
        review_results = [r for r in results if r.outcome == RuleOutcome.REVIEW.value]
        severities_present = {Severity(r.severity) for r in review_results}
        highest_review_severity = next(s for s in SEVERITY_ORDER if s in severities_present).value
        await create_approval_requests_for_review(
            session,
            organization_id=organization_id,
            actor_id=actor_id,
            compliance_review_id=review.id,
            highest_review_severity=highest_review_severity,
        )
    else:
        decision = await create_decision_for_review(
            session,
            organization_id=organization_id,
            actor_id=actor_id,
            compliance_review_id=review.id,
            status=aggregate.status,
            supersedes_decision_id=supersedes_decision_id,
        )
        decision_id = decision.id

    return ReviewOutcome(review=review, decision_id=decision_id)


@dataclass(frozen=True)
class ReviewStaleness:
    """Result of `assess_review_staleness` (FEATURE-6.4, BR-DEC-004). Contains only
    primitives so approvals can consume it without importing this module's types.

    `contract_version_id` is the version a fresh re-evaluation should run against: the
    newest analyzed version of the same Contract when `contract_changed`, otherwise the
    review's own version unchanged."""

    contract_version_id: uuid.UUID
    contract_changed: bool
    policy_changed: bool


async def assess_review_staleness(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> ReviewStaleness:
    """Read-only. Whether the inputs a review was computed from have been superseded:

    - `contract_changed`: a newer `analyzed` ContractVersion of the same Contract exists.
    - `policy_changed`: the organization's CURRENT set of published PolicyVersion ids differs
      from the set the review pooled, in EITHER direction (FEATURE-6.5): a newly published
      Policy (including the first policy ever, for a review that pooled none), a republished
      one (its old version is no longer current), or a pooled one that is no longer current.
      This is deliberately conservative: ANY change to the pooled set counts as material, even
      one that touched no rule the review actually evaluated. A finer, rule-level diff is
      future work -- the lean is toward re-evaluating.

    Raises `ComplianceReviewNotFoundError` if the review isn't in this organization."""
    review = await ComplianceReviewRepository(session).get_by_id_and_organization(
        compliance_review_id, organization_id
    )
    if review is None:
        raise ComplianceReviewNotFoundError()

    newer_contract_version_id = await get_newer_analyzed_contract_version_id(
        session, organization_id=organization_id, contract_version_id=review.contract_version_id
    )

    pooled_ids = {uuid.UUID(policy_version_id) for policy_version_id in review.policy_version_ids}
    current_ids = await PolicyVersionRepository(session).list_current_ids_by_organization(
        organization_id
    )
    policy_changed = current_ids != pooled_ids

    return ReviewStaleness(
        contract_version_id=newer_contract_version_id or review.contract_version_id,
        contract_changed=newer_contract_version_id is not None,
        policy_changed=policy_changed,
    )


async def get_review_supersedes_decision_id(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> uuid.UUID | None:
    """The `supersedes_decision_id` a review was created with (FEATURE-6.4) -- read by
    `approval_service`'s deferred path, which creates a REVIEW chain's Decision long after
    the review itself was persisted. `None` for any first-time review, or if the review
    isn't in this organization (the caller only ever passes a review it already loaded
    under the same organization, so a miss is a genuine inconsistency, not a tenant case)."""
    review = await ComplianceReviewRepository(session).get_by_id_and_organization(
        compliance_review_id, organization_id
    )
    return review.supersedes_decision_id if review is not None else None


async def get_review_contract_version_id(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> uuid.UUID | None:
    """The ContractVersion a review evaluated (FEATURE-6.5). Read by
    `decision_service.create_decision_for_review` so a Decision can be denormalised onto its
    ContractVersion. `None` if the review isn't in this organization -- the caller treats that
    as a refusal, never as "no version"."""
    review = await ComplianceReviewRepository(session).get_by_id_and_organization(
        compliance_review_id, organization_id
    )
    return review.contract_version_id if review is not None else None


async def count_reevaluation_attempts(
    session: AsyncSession, *, organization_id: uuid.UUID, decision_id: uuid.UUID
) -> int:
    """FEATURE-6.5 attempt count for a flagged Decision: the number of ComplianceReviews whose
    `supersedes_decision_id` is this Decision (BR-DEC-002). Tenant-scoped."""
    return await ComplianceReviewRepository(session).count_superseding(decision_id, organization_id)


async def list_reviews_for_contract_version(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> list[ComplianceReview]:
    """#62: the review-history read-model a contract detail page needs -- every
    `ComplianceReview` ever run against one `ContractVersion`, oldest first
    (`ComplianceReviewRepository.list_by_contract_version`'s own ordering) -- to show a
    review history / "already reviewed" state without the caller already knowing a
    `review_id`.

    Verifies tenant ownership of `contract_version_id` BEFORE listing, mirroring
    `trigger_review`'s check above and the QA/security fix already applied to
    `simulation_service.run_simulation` (2026-09-30): an empty list doesn't distinguish
    "no reviews yet" from "you don't own this contract version" to anyone probing ids, so
    a nonexistent or cross-tenant `contract_version_id` must 404, never silently return
    `[]`."""
    if not await contract_version_belongs_to_organization(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    ):
        raise ContractVersionNotFoundError()
    return await ComplianceReviewRepository(session).list_by_contract_version(
        contract_version_id, organization_id
    )


async def get_review_detail(
    session: AsyncSession, *, organization_id: uuid.UUID, review_id: uuid.UUID
) -> tuple[ComplianceReview, list[RuleEvaluation], list[Risk]]:
    """The read-model `GET /compliance/reviews/{id}` serves (#127/#62's backend half):
    one `ComplianceReview` with its full `RuleEvaluation` and `Risk` lists."""
    review = await ComplianceReviewRepository(session).get_by_id_and_organization(
        review_id, organization_id
    )
    if review is None:
        raise ComplianceReviewNotFoundError()
    evaluations = await RuleEvaluationRepository(session).list_by_review(review.id)
    risks = await RiskRepository(session).list_by_review(review.id)
    return review, evaluations, risks
