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

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.application.evidence_service import (
    contract_version_belongs_to_organization,
    get_evidence_refs_for_contract_version,
    get_supplier_id_for_contract_version,
)
from app.evidence.application.audit_service import emit_audit_event
from app.policies.application.context_builder import build_context_for_contract_version
from app.policies.application.evaluation_service import (
    AggregatePreview,
    RuleEvaluationResult,
    aggregate_preview,
    evaluate_policy_version,
)
from app.policies.domain.constants import ComplianceReviewStatus, RuleOutcome
from app.policies.domain.errors import ComplianceReviewNotFoundError, ContractVersionNotFoundError
from app.policies.domain.rule_dsl import referenced_paths_of
from app.policies.infrastructure.models import ComplianceReview, Risk, Rule, RuleEvaluation
from app.policies.infrastructure.repositories import (
    ComplianceReviewRepository,
    PolicyVersionRepository,
    RiskRepository,
    RuleEvaluationRepository,
    RuleRepository,
)
from app.suppliers.application.evidence_service import get_evidence_ref_for_supplier

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
    as one immutable `ComplianceReview` + its `RuleEvaluation`/`Risk` rows."""
    if not await contract_version_belongs_to_organization(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    ):
        raise ContractVersionNotFoundError()

    version_repo = PolicyVersionRepository(session)
    rule_repo = RuleRepository(session)
    policy_versions = await version_repo.list_current_by_organization(organization_id)

    rules: list[Rule] = []
    for policy_version in policy_versions:
        rules.extend(await rule_repo.list_by_version(policy_version.id))

    context = await build_context_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )

    review = ComplianceReview(
        organization_id=organization_id,
        contract_version_id=contract_version_id,
        policy_version_ids=[str(pv.id) for pv in policy_versions],
        status=ComplianceReviewStatus.IN_PROGRESS.value,
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

    results: list[RuleEvaluationResult] = evaluate_policy_version(rules, context)
    aggregate: AggregatePreview = aggregate_preview(results)

    supplier_id = await get_supplier_id_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )
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
            risk_repo.add(
                Risk(
                    compliance_review_id=review.id,
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

    await session.commit()
    await session.refresh(review)
    return review


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
