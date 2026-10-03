"""Re-evaluation of stale Decisions (FEATURE-6.4, STORY-6.4.1; FEATURE-6.5; DEC-003,
BR-DEC-002, BR-DEC-004; docs/03-domain/audit.md `compliance.review_required`).

## Detection is a periodic sweep, not a synchronous hook
A Decision goes stale three ways: its `valid_until` passes (`expired`), a newer
`ContractVersion` of its Contract is analyzed (`contract_changed`), or the organization's set
of published PolicyVersions changes in either direction (`policy_changed`, see
`compliance_review_service.assess_review_staleness`). Rather than having Contracts/Policies
push a notification into this context on every such write, the platform-wide sweep
(`reevaluate_stale_decisions`, Celery task `approvals.reevaluate_stale_decisions`) discovers
them. A Decision can look current for up to one sweep interval after the change that made it
stale. That window is the accepted cost.

## What the sweep does with each ACTIVE Decision (FEATURE-6.5)
Only the effective Decision (`lifecycle = ACTIVE`) is ever considered. A superseded Decision
is historical and is never touched again.

1. Fresh and stale and not overridden: flag it (`expired`/`contract_changed`/`policy_changed`),
   emit `compliance.review_required`, run a new ComplianceReview carrying
   `supersedes_decision_id`. The successor Decision, when it appears, supersedes this one.
2. Fresh, stale and overridden: flag it with `override_review_required` and emit
   `compliance.review_required` with that reason. NO review is run and no successor is
   created. A human must confirm the override or run a manual review, which supersedes it.
3. Flagged for an automatic reason, and the most recent re-evaluation review ended with an
   expired approval chain and produced no Decision (a "failed attempt"): retry, if the attempt
   count is below `settings.decision_reevaluation_max_attempts`. The attempt count is the
   number of ComplianceReviews whose `supersedes_decision_id` is this Decision.
4. Flagged, failed attempt, and the cap is reached: set `reevaluation_failed_at` once and emit
   `compliance.reevaluation_failed`. That event is the operator alert; a notification channel
   is future work. A non-null `reevaluation_failed_at` stops every further retry.

## Race safety
Every transition is an atomic conditional UPDATE, never a read-then-write:
- First flag: `flag_for_review_if_unflagged` (only one overlapping sweep can win).
- Retry: `claim_reevaluation_retry` compares-and-swaps `reevaluation_generation`. Two sweeps
  that observed the same failed attempt cannot both start a retry.
- Alert: `mark_reevaluation_failed_if_unmarked` sets `reevaluation_failed_at` once.
Each unit of work (flag or claim, plus the review and any Decision it produces) commits
together, or rolls back together, so a failure never leaves a Decision flagged with no review
and no way for the next sweep to see it.

## One unit of work per Decision
A failure anywhere rolls the unit back, so the Decision stays unflagged (or unclaimed) and
the next sweep retries it. One bad Decision never blocks the rest of the sweep. The
`last_checked_at` rotation stamp is written inside the same unit, so it commits with the work.

## Exception path (FEATURE-6.5 review follow-up, F4)
A rollback erases the flag, the claim and the review, so the attempt count above never grows
for an exception. Instead, after the rollback, the sweep records the failure in its OWN
committed transaction (`_record_failed_attempt`): `reevaluation_failure_count` is incremented
and `last_checked_at` is stamped. At `decision_reevaluation_max_attempts` the operator alert
is raised once, through the same set-once guard as step 4. The candidate query excludes a
Decision at the cap, so a deterministic exception cannot retry forever. The alert payload
uses the same keys; `attempts` is then the number of failed attempts that raised.

## Rotation (FEATURE-6.5 review follow-up, F3)
Every candidate the sweep evaluates gets `last_checked_at = now`, and the candidate query
orders by `coalesce(last_checked_at, created_at)`. A Decision that was just checked moves to
the back of the queue, so a batch of unchanged, healthy Decisions cannot starve newer stale
ones. A candidate whose evaluation raised is stamped by `_record_failed_attempt` for the same
reason: a failing Decision must rotate too. That stamp is the one deliberate case where a
rolled-back evaluation counts as checked.

## Judgment calls
- `contract_changed` re-evaluates against the NEWER analyzed version, not the one the prior
  Decision was built on. The successor describes the contract as it now stands.
- `policy_changed` is conservative: any change to the set of published policies, in either
  direction, counts. See `compliance_review_service.assess_review_staleness`.
- A REVIEW outcome on re-evaluation creates no successor Decision yet. The successor appears
  later, from `approval_service`'s deferred path, once the new chain resolves.
- A retry does not emit a second `compliance.review_required`. The Decision was flagged once;
  each retry is recorded by its own ComplianceReview, which carries the supersedes link.
- The return value counts re-evaluation reviews started (first attempts and retries). Override
  flags, failure alerts and failure-count records are not counted, because they run no review.
- An overridden Decision that hits the exception cap is excluded from further sweeps without an
  alert: the alert guard refuses overridden rows (F2), and a human already owns that outcome.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.constants import ReviewRequiredReason
from app.approvals.infrastructure.models import Decision
from app.approvals.infrastructure.repositories import DecisionRepository
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.policies.application.compliance_review_service import (
    assess_review_staleness,
    count_reevaluation_attempts,
    execute_review,
)

logger = logging.getLogger("jurisense.approvals.reevaluation")


@dataclass(frozen=True)
class _Candidate:
    """Snapshot of the fields the sweep needs, copied out before any commit/rollback.
    `session.rollback()` expires every loaded ORM instance, and reading an expired
    attribute from async code would trigger a lazy load that cannot run there."""

    decision_id: uuid.UUID
    organization_id: uuid.UUID
    compliance_review_id: uuid.UUID
    valid_until: datetime
    overridden: bool
    review_required_at: datetime | None
    reevaluation_generation: int
    last_reevaluation_review_id: uuid.UUID | None


def _as_utc(value: datetime) -> datetime:
    # SQLite (the test database) returns naive datetimes even for timezone=True columns.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def _determine_reason(
    session: AsyncSession, candidate: _Candidate, *, now: datetime
) -> tuple[ReviewRequiredReason, uuid.UUID] | None:
    """The single reason this Decision is stale (or `None` if it is still current), plus the
    ContractVersion a re-evaluation should run against."""
    staleness = await assess_review_staleness(
        session,
        organization_id=candidate.organization_id,
        compliance_review_id=candidate.compliance_review_id,
    )
    if _as_utc(candidate.valid_until) < now:
        reason = ReviewRequiredReason.EXPIRED
    elif staleness.contract_changed:
        reason = ReviewRequiredReason.CONTRACT_CHANGED
    elif staleness.policy_changed:
        reason = ReviewRequiredReason.POLICY_CHANGED
    else:
        return None
    return reason, staleness.contract_version_id


async def _emit_review_required(
    session: AsyncSession, candidate: _Candidate, *, reason: str, flagged_at: datetime
) -> None:
    await emit_audit_event(
        session,
        event_type="compliance.review_required",
        actor_id=None,
        organization_id=candidate.organization_id,
        payload={
            "decision_id": str(candidate.decision_id),
            "reason": reason,
            "flagged_at": flagged_at.isoformat(),
        },
    )


async def _flag_and_reevaluate(session: AsyncSession, candidate: _Candidate) -> bool:
    """Fresh (unflagged) candidate: flag it, then re-evaluate it, unless it carries a human
    override, in which case it is only flagged for a human (FEATURE-6.5, item 3). Writes only;
    the caller commits the unit."""
    now = datetime.now(UTC)
    determination = await _determine_reason(session, candidate, now=now)
    if determination is None:
        return False
    reason, contract_version_id = determination

    repository = DecisionRepository(session)
    flagged_at = datetime.now(UTC)
    if candidate.overridden:
        # A human decided this outcome. The system never replaces it silently: flag it, leave
        # it ACTIVE, run nothing. The flag column is the record that it was reviewed for
        # staleness, so the next sweep leaves it alone.
        won = await repository.flag_for_review_if_unflagged(
            candidate.decision_id,
            organization_id=candidate.organization_id,
            reason=ReviewRequiredReason.OVERRIDE_REVIEW_REQUIRED.value,
            flagged_at=flagged_at,
            expected_overridden=True,
        )
        if won:
            await _emit_review_required(
                session,
                candidate,
                reason=ReviewRequiredReason.OVERRIDE_REVIEW_REQUIRED.value,
                flagged_at=flagged_at,
            )
        return False

    # The race guard: only the one caller whose conditional UPDATE matches the row may
    # continue. An overlapping sweep that already flagged this Decision gets False here
    # and must not re-evaluate it or emit a second event.
    won = await repository.flag_for_review_if_unflagged(
        candidate.decision_id,
        organization_id=candidate.organization_id,
        reason=reason.value,
        flagged_at=flagged_at,
        expected_overridden=False,
    )
    if not won:
        return False

    await _emit_review_required(session, candidate, reason=reason.value, flagged_at=flagged_at)
    review = await execute_review(
        session,
        organization_id=candidate.organization_id,
        actor_id=None,
        contract_version_id=contract_version_id,
        supersedes_decision_id=candidate.decision_id,
    )
    await repository.set_last_reevaluation_review(
        candidate.decision_id, organization_id=candidate.organization_id, review_id=review.id
    )
    return True


async def _retry_flagged(session: AsyncSession, candidate: _Candidate) -> bool:
    """Flagged candidate whose last re-evaluation failed (its approval chain expired with no
    Decision): retry it, or, at the attempt cap, raise the one-time operator alert
    (FEATURE-6.5, item 4). Writes only; the caller commits the unit."""
    if candidate.last_reevaluation_review_id is None:
        # The sweep only selects a retry when a prior attempt exists; a flag with no attempt
        # behind it is not something this path may act on.
        return False

    repository = DecisionRepository(session)
    attempts = await count_reevaluation_attempts(
        session, organization_id=candidate.organization_id, decision_id=candidate.decision_id
    )
    now = datetime.now(UTC)
    if attempts >= get_settings().decision_reevaluation_max_attempts:
        won = await repository.mark_reevaluation_failed_if_unmarked(
            candidate.decision_id,
            organization_id=candidate.organization_id,
            observed_generation=candidate.reevaluation_generation,
            failed_at=now,
        )
        if won:
            await emit_audit_event(
                session,
                event_type="compliance.reevaluation_failed",
                actor_id=None,
                organization_id=candidate.organization_id,
                payload={
                    "decision_id": str(candidate.decision_id),
                    "attempts": attempts,
                    "last_review_id": str(candidate.last_reevaluation_review_id),
                    "failed_at": now.isoformat(),
                },
            )
        return False

    claimed = await repository.claim_reevaluation_retry(
        candidate.decision_id,
        organization_id=candidate.organization_id,
        observed_generation=candidate.reevaluation_generation,
    )
    if not claimed:
        return False

    staleness = await assess_review_staleness(
        session,
        organization_id=candidate.organization_id,
        compliance_review_id=candidate.compliance_review_id,
    )
    review = await execute_review(
        session,
        organization_id=candidate.organization_id,
        actor_id=None,
        contract_version_id=staleness.contract_version_id,
        supersedes_decision_id=candidate.decision_id,
    )
    await repository.set_last_reevaluation_review(
        candidate.decision_id, organization_id=candidate.organization_id, review_id=review.id
    )
    return True


async def _process_candidate(session: AsyncSession, candidate: _Candidate) -> bool:
    if candidate.review_required_at is None:
        return await _flag_and_reevaluate(session, candidate)
    return await _retry_flagged(session, candidate)


async def _record_failed_attempt(
    session: AsyncSession, candidate: _Candidate, *, checked_at: datetime
) -> None:
    """Exception path (F4). Called after the candidate's unit rolled back, in its own committed
    transaction: counts the failed attempt, stamps the check (so the Decision rotates), and at
    the attempt cap raises the one-time operator alert. Without this record, a deterministic
    exception rolls back to the same state every sweep and retries forever."""
    repository = DecisionRepository(session)
    max_attempts = get_settings().decision_reevaluation_max_attempts
    failures = await repository.increment_reevaluation_failure(
        candidate.decision_id, organization_id=candidate.organization_id, checked_at=checked_at
    )
    if failures is not None and failures >= max_attempts:
        won = await repository.mark_reevaluation_failed_if_unmarked(
            candidate.decision_id,
            organization_id=candidate.organization_id,
            observed_generation=None,
            failed_at=checked_at,
        )
        if won:
            await emit_audit_event(
                session,
                event_type="compliance.reevaluation_failed",
                actor_id=None,
                organization_id=candidate.organization_id,
                payload={
                    "decision_id": str(candidate.decision_id),
                    "attempts": failures,
                    "last_review_id": str(candidate.last_reevaluation_review_id)
                    if candidate.last_reevaluation_review_id is not None
                    else None,
                    "failed_at": checked_at.isoformat(),
                },
            )
    await session.commit()


def _candidate_of(decision: Decision) -> _Candidate:
    return _Candidate(
        decision_id=decision.id,
        organization_id=decision.organization_id,
        compliance_review_id=decision.compliance_review_id,
        valid_until=decision.valid_until,
        overridden=decision.overridden,
        review_required_at=decision.review_required_at,
        reevaluation_generation=decision.reevaluation_generation,
        last_reevaluation_review_id=decision.last_reevaluation_review_id,
    )


async def reevaluate_stale_decisions(session: AsyncSession) -> int:
    """Runs one sweep over the effective Decisions in every organization, returning how many
    re-evaluation reviews this call started (first attempts and retries). Commits per
    Decision, not once at the end: each unit of work is its own transaction (see the module
    docstring).

    The candidate read is capped at the batch size and rotates (oldest `last_checked_at`
    first), so repeated sweeps drain the whole backlog rather than re-reading the same rows.

    Tenant isolation: every read and write uses the candidate Decision's own
    `organization_id`, so one organization's staleness can never touch another's data.
    """
    settings = get_settings()
    candidates = [
        _candidate_of(decision)
        for decision in await DecisionRepository(session).list_reevaluation_candidates(
            limit=settings.decision_reevaluation_batch_size,
            max_failures=settings.decision_reevaluation_max_attempts,
        )
    ]

    reevaluated = 0
    for candidate in candidates:
        checked_at = datetime.now(UTC)
        try:
            started = await _process_candidate(session, candidate)
            await DecisionRepository(session).mark_checked(
                candidate.decision_id,
                organization_id=candidate.organization_id,
                checked_at=checked_at,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Re-evaluation failed for decision %s; the failure is recorded and it will be "
                "retried on a later sweep until the attempt cap",
                candidate.decision_id,
            )
            try:
                await _record_failed_attempt(session, candidate, checked_at=checked_at)
            except Exception:
                await session.rollback()
                logger.exception(
                    "Could not record the failed re-evaluation attempt for decision %s",
                    candidate.decision_id,
                )
            continue
        if started:
            reevaluated += 1
    return reevaluated
