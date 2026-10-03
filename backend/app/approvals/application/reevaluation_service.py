"""Re-evaluation of stale Decisions (FEATURE-6.4, STORY-6.4.1; DEC-003, BR-DEC-002,
BR-DEC-004; docs/03-domain/audit.md `compliance.review_required`).

## Detection is a periodic sweep, not a synchronous hook
A Decision goes stale three ways: its `valid_until` passes (`expired`), a newer
`ContractVersion` of its Contract is analyzed (`contract_changed`), or a PolicyVersion it
was evaluated under is superseded (`policy_changed`). Rather than having Contracts/Policies
push a notification into this context on every such write, the platform-wide sweep
(`reevaluate_stale_decisions`, Celery task `approvals.reevaluate_stale_decisions`) discovers
them. This avoids a new write-side cross-context hook and is eventually consistent by
design: a Decision can look current for up to one sweep interval
(`settings.decision_reevaluation_interval_seconds`, hourly by default and a TBD) after the
change that made it stale. That window is the accepted cost.

## One unit of work per Decision
For each candidate: flag it (atomic conditional UPDATE), emit `compliance.review_required`,
run the new ComplianceReview (`execute_review`, which carries `supersedes_decision_id`),
then commit once. A failure anywhere rolls the flag back, so the Decision stays unflagged
and the next sweep retries it. One bad Decision never blocks the rest of the sweep.

## Judgment calls
- `contract_changed` re-evaluates against the NEWER analyzed version, not the one the prior
  Decision was built on. The successor describes the contract as it now stands.
- `policy_changed` is conservative: any newer publish of a pooled policy counts. See
  `compliance_review_service.assess_review_staleness`.
- A REVIEW outcome on re-evaluation creates no successor Decision yet. The successor
  appears later, from `approval_service`'s deferred path, once the new chain resolves.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.constants import ReviewRequiredReason
from app.approvals.infrastructure.repositories import DecisionRepository
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.policies.application.compliance_review_service import (
    assess_review_staleness,
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


def _as_utc(value: datetime) -> datetime:
    # SQLite (the test database) returns naive datetimes even for timezone=True columns.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def _determine_reason(
    session: AsyncSession, candidate: _Candidate, *, now: datetime
) -> tuple[ReviewRequiredReason, uuid.UUID] | None:
    """The single reason to flag this Decision (or `None` if it is still current), plus
    the ContractVersion a re-evaluation should run against."""
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


async def _reevaluate_one(session: AsyncSession, candidate: _Candidate) -> bool:
    determination = await _determine_reason(session, candidate, now=datetime.now(UTC))
    if determination is None:
        return False
    reason, contract_version_id = determination

    flagged_at = datetime.now(UTC)
    # The race guard: only the one caller whose conditional UPDATE matches the row may
    # continue. An overlapping sweep that already flagged this Decision gets False here
    # and must not re-evaluate it or emit a second event.
    won = await DecisionRepository(session).flag_for_review_if_unflagged(
        candidate.decision_id,
        organization_id=candidate.organization_id,
        reason=reason.value,
        flagged_at=flagged_at,
    )
    if not won:
        return False

    await emit_audit_event(
        session,
        event_type="compliance.review_required",
        actor_id=None,
        organization_id=candidate.organization_id,
        payload={
            "decision_id": str(candidate.decision_id),
            "reason": reason.value,
            "flagged_at": flagged_at.isoformat(),
        },
    )
    await execute_review(
        session,
        organization_id=candidate.organization_id,
        actor_id=None,
        contract_version_id=contract_version_id,
        supersedes_decision_id=candidate.decision_id,
    )
    await session.commit()
    return True


async def reevaluate_stale_decisions(session: AsyncSession) -> int:
    """Flags and re-evaluates every stale Decision across all organizations, returning how
    many were re-evaluated by this call. Commits per Decision, not once at the end: each
    re-evaluation is its own unit of work (see the module docstring).

    Tenant isolation: every read and write uses the flagged Decision's own
    `organization_id`, so one organization's staleness can never touch another's data.
    """
    candidates = [
        _Candidate(
            decision_id=decision.id,
            organization_id=decision.organization_id,
            compliance_review_id=decision.compliance_review_id,
            valid_until=decision.valid_until,
        )
        for decision in await DecisionRepository(session).list_reevaluation_candidates(
            limit=get_settings().decision_reevaluation_batch_size
        )
    ]

    reevaluated = 0
    for candidate in candidates:
        try:
            if await _reevaluate_one(session, candidate):
                reevaluated += 1
        except Exception:
            await session.rollback()
            logger.exception(
                "Re-evaluation failed for decision %s; it stays unflagged and will be "
                "retried on the next sweep",
                candidate.decision_id,
            )
    await session.commit()
    return reevaluated
