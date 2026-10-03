import uuid
from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.approvals.domain.constants import (
    ApprovalRequestStatus,
    DecisionLifecycle,
    ReviewRequiredReason,
)
from app.approvals.infrastructure.models import ApprovalRequest, ApprovalWorkflow, Decision
from app.core.config import get_settings


class ApprovalWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, workflow: ApprovalWorkflow) -> None:
        self._session.add(workflow)

    async def get_by_organization_and_trigger(
        self, organization_id: uuid.UUID, trigger_condition: str
    ) -> ApprovalWorkflow | None:
        result = await self._session.execute(
            select(ApprovalWorkflow).where(
                ApprovalWorkflow.organization_id == organization_id,
                ApprovalWorkflow.trigger_condition == trigger_condition,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, workflow_id: uuid.UUID) -> ApprovalWorkflow | None:
        return await self._session.get(ApprovalWorkflow, workflow_id)

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[ApprovalWorkflow]:
        result = await self._session.execute(
            select(ApprovalWorkflow).where(ApprovalWorkflow.organization_id == organization_id)
        )
        return list(result.scalars())


class ApprovalRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, request: ApprovalRequest) -> None:
        self._session.add(request)

    async def get_by_id_and_organization(
        self, request_id: uuid.UUID, organization_id: uuid.UUID
    ) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_review(
        self, compliance_review_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ApprovalRequest]:
        result = await self._session.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.compliance_review_id == compliance_review_id,
                ApprovalRequest.organization_id == organization_id,
            )
            .order_by(ApprovalRequest.step_number)
        )
        return list(result.scalars())

    async def list_pending_requested_before(self, cutoff: datetime) -> list[ApprovalRequest]:
        """BR-APR-003 SLA expiry: every `pending` request whose `requested_at` is older
        than `cutoff` -- across every organization, since the Celery task
        (`app.approvals.infrastructure.tasks.expire_stale_approval_requests_task`) runs
        platform-wide, not per-tenant. Used only to discover *candidates* for the audit
        event payload (id/organization_id/approver_role/etc.) -- the actual transition is
        `expire_pending_if_pending` below, never a plain attribute mutation on the objects
        this returns (see that method's docstring for why)."""
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
                ApprovalRequest.requested_at < cutoff,
            )
        )
        return list(result.scalars())

    async def resolve_if_pending(
        self,
        request_id: uuid.UUID,
        *,
        status: str,
        justification: str | None,
        resolved_by: uuid.UUID,
        resolved_at: datetime,
    ) -> bool:
        """QA/security review (2026-10-01): `approve_request`/`reject_request` previously
        loaded the row, checked `status == PENDING` in Python, then mutated ORM attributes
        and flushed -- a classic read-then-write race. Two callers (two users who both
        hold the required `approver_role`, or one approving while another rejects the same
        step) could both pass the Python check before either committed, both proceed to
        instantiate a next step or create a `Decision`, and silently produce duplicate/
        contradictory rows with no error surfaced to either caller (both get 200).

        This is a single atomic `UPDATE ... WHERE id = :id AND status = 'pending'`,
        executed via SQLAlchemy Core (bypassing `ApprovalRequest._guard_resolved`'s
        `@validates` hooks entirely, since a Core-level bulk update never touches ORM
        instance attributes) -- the database's own row-level locking during the UPDATE is
        what actually serializes two concurrent resolution attempts now, not a
        Python-level check. Returns `True` if this call won the race (exactly one caller
        ever does, for any given request); `False` means another transaction already
        resolved it -- the caller must treat that as `ApprovalRequestAlreadyResolvedError`,
        exactly as if the earlier Python-level check had caught it.

        Callers must `session.refresh()` the ORM object afterward if they continue using
        it -- this bypasses the identity map's normal attribute-tracking, so the in-memory
        object is stale (still shows `status="pending"`) until refreshed."""
        result = await self._session.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
            )
            .values(
                status=status,
                justification=justification,
                resolved_by=resolved_by,
                resolved_at=resolved_at,
            )
        )
        return result.rowcount > 0

    async def expire_pending_if_pending(self, request_id: uuid.UUID) -> bool:
        """The SLA-sweep side of the same race `resolve_if_pending` closes from the human
        side (QA/security review, 2026-10-01): the Celery task's own transition must be an
        equally atomic conditional `UPDATE`, or a human's `approve`/`reject` landing
        between this task's `SELECT` (`list_pending_requested_before`) and its old
        load-then-mutate `commit()` could have its result silently clobbered back to
        `expired` with no error on either side. Returns `True` only if THIS call
        transitioned the row (still `pending` at UPDATE time) -- `False` means a human (or
        a different worker run) already resolved it first, and the caller should skip
        emitting an `approval.expired` audit event for it. `ApprovalRequest` has no
        `expired_at` column of its own (only `resolved_at`, for a human resolution) -- the
        audit event's own `expired_at` payload field is a point-in-time value the caller
        generates, not something this method persists on the row."""
        result = await self._session.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
            )
            .values(status=ApprovalRequestStatus.EXPIRED.value)
        )
        return result.rowcount > 0


class DecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, decision: Decision) -> None:
        self._session.add(decision)

    async def get_by_id_and_organization(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Decision | None:
        result = await self._session.execute(
            select(Decision).where(
                Decision.id == decision_id, Decision.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_review(
        self, compliance_review_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Decision | None:
        result = await self._session.execute(
            select(Decision).where(
                Decision.compliance_review_id == compliance_review_id,
                Decision.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_active_for_contract_version(
        self, organization_id: uuid.UUID, contract_version_id: uuid.UUID
    ) -> list[Decision]:
        """The effective Decision(s) for one ContractVersion -- at most one, by the partial
        unique index; a list only so a caller never has to assume that."""
        result = await self._session.execute(
            select(Decision)
            .where(
                Decision.organization_id == organization_id,
                Decision.contract_version_id == contract_version_id,
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
            )
            .order_by(Decision.created_at)
        )
        return list(result.scalars())

    async def supersede_if_active(
        self, decision_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> bool:
        """Marks one Decision `SUPERSEDED` only if it is still `ACTIVE` (FEATURE-6.5). Only
        the lifecycle column is written -- the Decision's content is never edited (BR-DEC-002).
        Returns `False` if it was already superseded (a concurrent creation got there first),
        which the caller treats as a no-op rather than an error."""
        result = await self._session.execute(
            update(Decision)
            .where(
                Decision.id == decision_id,
                Decision.organization_id == organization_id,
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
            )
            .values(lifecycle=DecisionLifecycle.SUPERSEDED.value)
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount > 0

    async def list_reevaluation_candidates(
        self, *, limit: int, max_failures: int | None = None
    ) -> list[Decision]:
        """FEATURE-6.4/6.5 sweep candidates, platform-wide (like the SLA sweep), capped at
        `limit`. Two kinds, both restricted to the ACTIVE (effective) Decision:

        - Fresh: not yet flagged. The sweep decides whether it is stale.
        - Retry: flagged for an automatic reason (not an override), not yet alerted as failed,
          whose most recent re-evaluation review ended with an EXPIRED approval chain and
          produced no Decision. The sweep decides whether the attempt cap is reached.

        A flagged Decision that is not a retry candidate is never returned, which is what
        keeps repeated sweeps idempotent. A superseded Decision is never returned: it has
        already been replaced and must not be re-replaced.

        Rotation (F3): ordered by `coalesce(last_checked_at, created_at)` ascending, so the
        Decisions a sweep checked most recently go to the back of the queue. Without this, a
        `LIMIT` over `created_at` alone let the oldest unchanged Decisions fill every batch and
        newer stale ones were never reached.

        Exception cap (F4): a Decision whose re-evaluation has raised `max_failures` times is
        never returned again, even when it is not flagged (its failure never reached the flag).
        `max_failures` defaults to the configured attempt cap."""
        if max_failures is None:
            max_failures = get_settings().decision_reevaluation_max_attempts
        inner_decision = aliased(Decision)
        last_review_expired = exists(
            select(ApprovalRequest.id).where(
                ApprovalRequest.compliance_review_id == Decision.last_reevaluation_review_id,
                ApprovalRequest.status == ApprovalRequestStatus.EXPIRED.value,
            )
        )
        last_review_has_no_decision = ~exists(
            select(inner_decision.id).where(
                inner_decision.compliance_review_id == Decision.last_reevaluation_review_id
            )
        )
        is_fresh = Decision.review_required_at.is_(None)
        is_retry = and_(
            Decision.review_required_at.is_not(None),
            Decision.overridden.is_(False),
            Decision.review_required_reason != ReviewRequiredReason.OVERRIDE_REVIEW_REQUIRED.value,
            Decision.last_reevaluation_review_id.is_not(None),
            last_review_expired,
            last_review_has_no_decision,
        )
        result = await self._session.execute(
            select(Decision)
            .where(
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
                Decision.reevaluation_failed_at.is_(None),
                Decision.reevaluation_failure_count < max_failures,
                or_(is_fresh, is_retry),
            )
            .order_by(
                func.coalesce(Decision.last_checked_at, Decision.created_at).asc(),
                Decision.id,
            )
            .limit(limit)
        )
        return list(result.scalars())

    async def mark_checked(
        self, decision_id: uuid.UUID, *, organization_id: uuid.UUID, checked_at: datetime
    ) -> None:
        """Rotation stamp (F3): records that the sweep evaluated this Decision. The caller commits
        it in the same unit as that evaluation, so a rolled-back evaluation is not counted as
        checked -- unless it failed, in which case `increment_reevaluation_failure` records the
        check in its own transaction, deliberately, so a failing Decision also rotates."""
        await self._session.execute(
            update(Decision)
            .where(Decision.id == decision_id, Decision.organization_id == organization_id)
            .values(last_checked_at=checked_at)
        )

    async def increment_reevaluation_failure(
        self, decision_id: uuid.UUID, *, organization_id: uuid.UUID, checked_at: datetime
    ) -> int | None:
        """Exception path (F4): counts one re-evaluation attempt that raised, and stamps the check.
        Returns the new failure count, or `None` if the Decision is no longer an effective,
        unalerted Decision in this organization (nothing was counted). The caller commits."""
        result = await self._session.execute(
            update(Decision)
            .where(
                Decision.id == decision_id,
                Decision.organization_id == organization_id,
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
                Decision.reevaluation_failed_at.is_(None),
            )
            .values(
                reevaluation_failure_count=Decision.reevaluation_failure_count + 1,
                last_checked_at=checked_at,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 0:
            return None
        count = await self._session.execute(
            select(Decision.reevaluation_failure_count).where(
                Decision.id == decision_id, Decision.organization_id == organization_id
            )
        )
        return int(count.scalar_one())

    async def flag_for_review_if_unflagged(
        self,
        decision_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        reason: str,
        flagged_at: datetime,
        expected_overridden: bool = False,
    ) -> bool:
        """Atomically sets `review_required_at`/`review_required_reason` (BR-DEC-004),
        only if still unset. Same atomic conditional-UPDATE pattern as
        `ApprovalRequestRepository.resolve_if_pending` (see its docstring for the race
        this closes): two overlapping sweeps both reading the same Decision as stale
        cannot both win -- the database serializes the two UPDATEs, and only the first one
        matches a row. Returns `True` only for the single caller that flagged it; that
        caller alone may re-evaluate and emit `compliance.review_required`.

        FEATURE-6.5: the flag also requires the Decision to still be ACTIVE and to still have
        the override state the sweep observed (`expected_overridden`). Without that, a human
        override or a supersession committed after the sweep's snapshot could be re-evaluated
        over. A mismatch matches no row, so the next sweep re-reads and decides again."""
        result = await self._session.execute(
            update(Decision)
            .where(
                Decision.id == decision_id,
                Decision.organization_id == organization_id,
                Decision.review_required_at.is_(None),
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
                Decision.overridden.is_(expected_overridden),
            )
            .values(review_required_at=flagged_at, review_required_reason=reason)
        )
        return result.rowcount > 0

    async def set_last_reevaluation_review(
        self,
        decision_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        review_id: uuid.UUID,
    ) -> None:
        """Records the re-evaluation review a sweep just ran for this Decision. Only ever
        called by the caller that holds the flag or the retry claim for it, so it needs no
        compare-and-swap of its own."""
        await self._session.execute(
            update(Decision)
            .where(Decision.id == decision_id, Decision.organization_id == organization_id)
            .values(last_reevaluation_review_id=review_id)
        )

    async def claim_reevaluation_retry(
        self,
        decision_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        observed_generation: int,
    ) -> bool:
        """FEATURE-6.5 retry claim: a compare-and-swap on `reevaluation_generation`. Exactly
        one of two overlapping sweeps that both observed the same generation can win; the
        other finds the generation already advanced and starts nothing. Refuses anything no
        longer retryable (superseded, overridden, already alerted) in the same statement."""
        result = await self._session.execute(
            update(Decision)
            .where(
                Decision.id == decision_id,
                Decision.organization_id == organization_id,
                Decision.reevaluation_generation == observed_generation,
                Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
                Decision.overridden.is_(False),
                Decision.reevaluation_failed_at.is_(None),
            )
            .values(reevaluation_generation=Decision.reevaluation_generation + 1)
        )
        return result.rowcount > 0

    async def mark_reevaluation_failed_if_unmarked(
        self,
        decision_id: uuid.UUID,
        *,
        organization_id: uuid.UUID,
        observed_generation: int | None,
        failed_at: datetime,
    ) -> bool:
        """FEATURE-6.5 cap reached: sets `reevaluation_failed_at` exactly once, so the
        `compliance.reevaluation_failed` operator alert is emitted by one caller only.

        `observed_generation` guards the retry path (the cap was observed at that generation). The
        exception path (F4) passes `None`: its cap is a failure count, not a generation.

        Never alerts on an overridden Decision (F2): an override after the sweep's snapshot means a
        human now owns the outcome, so an automatic-retry alert would be wrong. The override
        guard also applies to the exception path, which then stops retrying without an alert."""
        conditions = [
            Decision.id == decision_id,
            Decision.organization_id == organization_id,
            Decision.lifecycle == DecisionLifecycle.ACTIVE.value,
            Decision.reevaluation_failed_at.is_(None),
            Decision.overridden.is_(False),
        ]
        if observed_generation is not None:
            conditions.append(Decision.reevaluation_generation == observed_generation)
        result = await self._session.execute(
            update(Decision).where(*conditions).values(reevaluation_failed_at=failed_at)
        )
        return result.rowcount > 0
