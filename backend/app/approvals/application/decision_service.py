"""Decision assembly and manual override (FEATURE-6.3, DEC-001/DEC-002; BR-DEC-001/
BR-DEC-003; docs/03-domain/domain-model.md "Decision").
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.constants import DecisionLifecycle
from app.approvals.domain.errors import (
    DecisionAlreadyExistsError,
    DecisionNotEffectiveError,
    DecisionNotFoundError,
    DecisionReviewNotFoundError,
    EmptyJustificationError,
    OverriddenDecisionSupersessionError,
)
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event


async def create_decision_for_review(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    compliance_review_id: uuid.UUID,
    status: str,
    supersedes_decision_id: uuid.UUID | None = None,
) -> Decision:
    """Creates the final, packaged `Decision` for one `ComplianceReview` (DEC-001,
    BR-DEC-001) and makes it the single effective Decision for its ContractVersion
    (FEATURE-6.5, BR-DEC-002).

    Effectiveness, in one transaction (the caller commits):
    1. Every Decision that is `ACTIVE` for this review's ContractVersion, plus the explicit
       `supersedes_decision_id` if given, is marked `SUPERSEDED`. The explicit target is
       included because a re-evaluation against a NEWER ContractVersion (`contract_changed`)
       would otherwise leave its predecessor, which belongs to the older version, `ACTIVE`
       forever. Each is a conditional UPDATE (`supersede_if_active`), so a concurrent
       creation that already superseded it is a no-op.
    2. The new Decision is inserted `ACTIVE`, with `supersedes_decision_id` set to the explicit
       target, or -- when none was given -- to the Decision that was ACTIVE for the version.
       This is how a manual review (no supersedes link) still replaces the previous effective
       Decision, including when a re-evaluation chain completes after it.
    3. If the partial unique index on `(contract_version_id) WHERE lifecycle = 'ACTIVE'` (or the
       one-per-review constraint) rejects the insert, the whole transaction is rolled back --
       so a superseded predecessor is never left without a successor -- and
       `DecisionAlreadyExistsError` is raised instead of a raw IntegrityError. Only those two
       known uniqueness constraints are mapped; any other integrity error (a foreign key, a
       NOT NULL) is a bug and is re-raised unchanged.

    F1 (BR-DEC-003, override is a human decision): when `supersedes_decision_id` is given (the
    automatic re-evaluation path), a Decision that is `overridden` and currently `ACTIVE` is never
    superseded silently. If the explicit target, or any other ACTIVE Decision of the version,
    is overridden, `OverriddenDecisionSupersessionError` is raised before any write. A manual
    review (no supersedes link) still supersedes an overridden ACTIVE Decision: a human may
    replace an override.

    `supersedes_decision_id` is validated against the caller's organization (ADR-003): a
    foreign id raises `DecisionNotFoundError` before anything is written.

    Two distinct call sites, per the epic's "critical timing nuance":
    - `app.policies.application.compliance_review_service.execute_review` calls this directly,
      in the SAME transaction as the review it just completed, for an aggregate `APPROVE` or
      `BLOCK` outcome -- no human approval step is needed for either
      (docs/03-domain/approvals.md: "BLOCK is not reviewable through this workflow").
    - `approval_service.approve_request`/`reject_request` call this once an approval chain for a
      `REVIEW`-outcome review reaches a terminal state. A `REVIEW`-outcome review has no
      `Decision` row at all while its chain is still pending, so the supersession of whatever
      was ACTIVE is decided at THIS moment, not when the review was triggered.

    `valid_until`'s exact duration is a documented `TBD` (BR-DEC-004 doesn't pin a number)
    -- `settings.decision_valid_days` (default 90 days) is a plain, defensible default.

    Does not commit -- the caller commits once at the end of its own use case.

    QA/security review (2026-10-01): `decisions.compliance_review_id` carries a unique
    constraint as defense-in-depth against two concurrent `approve_request` calls on the same
    chain's final step both reaching this function.
    """
    contract_version_id = await _contract_version_of_review(
        session, organization_id=organization_id, compliance_review_id=compliance_review_id
    )
    explicit_target: Decision | None = None
    if supersedes_decision_id is not None:
        # ADR-003: a supersedes link must never cross tenants. get_decision is org-scoped.
        explicit_target = await get_decision(
            session, organization_id=organization_id, decision_id=supersedes_decision_id
        )

    repository = DecisionRepository(session)
    active_for_version = await repository.list_active_for_contract_version(
        organization_id, contract_version_id
    )
    to_supersede: list[uuid.UUID] = []
    if supersedes_decision_id is not None:
        to_supersede.append(supersedes_decision_id)
    for active in active_for_version:
        if active.id not in to_supersede:
            to_supersede.append(active.id)

    if supersedes_decision_id is not None:
        # F1: refuse before any write. An automatic chain never replaces a human's override.
        effective_rows = list(active_for_version)
        if (
            explicit_target is not None
            and explicit_target.lifecycle == DecisionLifecycle.ACTIVE.value
        ):
            effective_rows.append(explicit_target)
        if any(row.overridden for row in effective_rows):
            raise OverriddenDecisionSupersessionError()

    superseded_ids: list[uuid.UUID] = []
    for decision_id in to_supersede:
        if await repository.supersede_if_active(decision_id, organization_id=organization_id):
            superseded_ids.append(decision_id)

    if supersedes_decision_id is None and active_for_version:
        supersedes_decision_id = active_for_version[0].id

    settings = get_settings()
    now = datetime.now(UTC)
    decision = Decision(
        organization_id=organization_id,
        compliance_review_id=compliance_review_id,
        contract_version_id=contract_version_id,
        lifecycle=DecisionLifecycle.ACTIVE.value,
        status=status,
        valid_until=now + timedelta(days=settings.decision_valid_days),
        supersedes_decision_id=supersedes_decision_id,
    )
    repository.add(decision)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if _is_known_uniqueness_violation(exc):
            raise DecisionAlreadyExistsError() from exc
        raise

    await emit_audit_event(
        session,
        event_type="decision.created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "decision_id": str(decision.id),
            "compliance_review_id": str(compliance_review_id),
            "status": decision.status,
            "valid_until": decision.valid_until.isoformat(),
            "supersedes_decision_id": str(supersedes_decision_id)
            if supersedes_decision_id is not None
            else None,
            "superseded_decision_ids": sorted(str(i) for i in superseded_ids),
            "created_at": now.isoformat(),
        },
    )
    return decision


# The only two uniqueness constraints this insert can legitimately hit, matched by constraint
# name (PostgreSQL) or by the column the SQLite message names (the test database).
_KNOWN_UNIQUENESS_MARKERS: tuple[tuple[str, str], ...] = (
    ("uq_decisions_one_per_compliance_review", "decisions.compliance_review_id"),
    ("uq_decisions_one_active_per_contract_version", "decisions.contract_version_id"),
)


def _is_known_uniqueness_violation(exc: IntegrityError) -> bool:
    """True only when the driver error reports a uniqueness violation on one of the two known
    constraints. A foreign-key or NOT NULL failure, or a unique violation elsewhere, is not one."""
    text = f"{exc.orig} {getattr(exc.orig, '__cause__', '') or ''}".lower()
    if "unique" not in text:
        return False
    return any(name in text or column in text for name, column in _KNOWN_UNIQUENESS_MARKERS)


async def _contract_version_of_review(
    session: AsyncSession, *, organization_id: uuid.UUID, compliance_review_id: uuid.UUID
) -> uuid.UUID:
    # Imported inside the function: policies imports this module at its own top level, so a
    # module-level import here would be circular (same pattern as approval_service).
    from app.policies.application.compliance_review_service import (
        get_review_contract_version_id,
    )

    contract_version_id = await get_review_contract_version_id(
        session, organization_id=organization_id, compliance_review_id=compliance_review_id
    )
    if contract_version_id is None:
        raise DecisionReviewNotFoundError()
    return contract_version_id


async def get_decision(
    session: AsyncSession, *, organization_id: uuid.UUID, decision_id: uuid.UUID
) -> Decision:
    decision = await DecisionRepository(session).get_by_id_and_organization(
        decision_id, organization_id
    )
    if decision is None:
        raise DecisionNotFoundError()
    return decision


async def override_decision(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    decision_id: uuid.UUID,
    new_status: str,
    justification: str,
) -> Decision:
    """Unlike `create_decision_for_review` (always a sub-step of another use case's own
    transaction), this function IS the entry use case for `POST /decisions/{id}/override`
    -- it commits itself, same as `compliance_review_service.trigger_review` or
    `approval_service.approve_request` do at the end of theirs.

    DEC-002/BR-DEC-003: authorized manual override with mandatory, non-empty
    justification. Sets `overridden`/`override_justification` and changes `status` in
    place -- the one documented exception to "a Decision is never edited in place"
    (that invariant is about *re-evaluation*, domain-model.md; override is a distinct,
    explicitly-modeled mutation path, see `Decision`'s own docstring). Never touches the
    underlying `RuleEvaluation`/`ApprovalRequest` records (BR-DEC-003: "without deleting
    the original evaluation record") -- this function doesn't even import those models.
    """
    if not justification or not justification.strip():
        raise EmptyJustificationError()

    decision = await get_decision(session, organization_id=organization_id, decision_id=decision_id)
    original_status = decision.status
    now = datetime.now(UTC)

    # F1 (BR-DEC-002/BR-DEC-003): a conditional UPDATE, so only an ACTIVE Decision can be
    # overridden. Matching no row means it was superseded (or superseded concurrently): refuse
    # with nothing written, instead of editing a historical record.
    result = await session.execute(
        update(Decision)
        .where(
            Decision.id == decision_id,
            Decision.organization_id == organization_id,
            Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
        )
        .values(overridden=True, override_justification=justification, status=new_status)
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount == 0:
        raise DecisionNotEffectiveError()

    await emit_audit_event(
        session,
        event_type="decision.overridden",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "decision_id": str(decision.id),
            "original_outcome": original_status,
            "new_outcome": new_status,
            "justification": justification,
            "overridden_by": str(actor_id),
            "overridden_at": now.isoformat(),
        },
    )
    await session.commit()
    await session.refresh(decision)
    return decision
