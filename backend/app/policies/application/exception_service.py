"""`PolicyException` grant flow (#120, STORY-4.4.2; docs/03-domain/policy-engine.md
"Exceptions & manual overrides"): lets an approver waive one REVIEW-tier `Rule` for one
Supplier or ContractVersion, for a bounded time window, with a mandatory justification.

Sign-off model: the actor granting the exception must themselves hold an ACTIVE
`Membership` whose `role` equals the waived rule's own `approver_role` -- the same role
that would otherwise have to approve a real `ApprovalRequest` this rule's REVIEW outcome
produces. `_resolve_actor_role` below is a local equivalent of
`app.approvals.application.approval_service._resolve_actor_role` (that function is
private to its own context and not importable across the boundary); both resolve to the
exact same underlying `MembershipRepository`/`MembershipStatus` primitives from
`app.identity`, so the two can never disagree about what "this user's role in this
organization" means.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.application.evidence_service import contract_version_belongs_to_organization
from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.identity.domain.constants import MembershipStatus
from app.identity.infrastructure.repositories import MembershipRepository
from app.policies.application import rule_service
from app.policies.domain.errors import (
    ActiveExceptionLimitExceededError,
    ActorNotAuthorizedForExceptionError,
    ExceptionJustificationRequiredError,
    ExceptionTargetInvalidError,
    ExceptionTargetNotFoundError,
    ExceptionValidUntilMustBeFutureError,
    RuleNotEligibleForExceptionError,
)
from app.policies.infrastructure.models import PolicyException
from app.policies.infrastructure.repositories import PolicyExceptionRepository
from app.suppliers.application.evidence_service import get_supplier_identity


async def _resolve_actor_role(
    session: AsyncSession, *, user_id: uuid.UUID, organization_id: uuid.UUID
) -> str | None:
    membership = await MembershipRepository(session).get_by_user_and_organization(
        user_id, organization_id
    )
    if membership is None or membership.status != MembershipStatus.ACTIVE.value:
        return None
    return membership.role


async def grant_exception(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
    supplier_id: uuid.UUID | None,
    contract_version_id: uuid.UUID | None,
    justification: str,
    valid_until: datetime,
) -> PolicyException:
    if not justification.strip():
        raise ExceptionJustificationRequiredError()
    if (supplier_id is None) == (contract_version_id is None):
        raise ExceptionTargetInvalidError()
    # Code review (2026-10-12): a `valid_until` with no UTC offset (Pydantic v2 parses
    # "2026-11-01T00:00:00" into a naive datetime) previously crashed this comparison
    # with an unhandled TypeError instead of the clean validation error below --
    # treating a bare timestamp as already UTC is this codebase's existing convention
    # for every other `DateTime(timezone=True)` column.
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=UTC)
    if valid_until <= datetime.now(UTC):
        raise ExceptionValidUntilMustBeFutureError()

    # Raises PolicyNotFoundError/PolicyVersionNotFoundError/RuleNotFoundError -- the same
    # 3-hop Rule -> PolicyVersion -> Policy.organization_id ownership check every other
    # rule-scoped route in this context already relies on.
    rule = await rule_service.get_rule(
        session,
        organization_id=organization_id,
        policy_id=policy_id,
        version_id=version_id,
        rule_id=rule_id,
    )
    if rule.approver_role is None:
        raise RuleNotEligibleForExceptionError()

    actor_role = await _resolve_actor_role(
        session, user_id=actor_id, organization_id=organization_id
    )
    if actor_role != rule.approver_role:
        raise ActorNotAuthorizedForExceptionError()

    if supplier_id is not None:
        if await get_supplier_identity(
            session, organization_id=organization_id, supplier_id=supplier_id
        ) is None:
            raise ExceptionTargetNotFoundError()
    else:
        if not await contract_version_belongs_to_organization(
            session, organization_id=organization_id, contract_version_id=contract_version_id
        ):
            raise ExceptionTargetNotFoundError()

    now = datetime.now(UTC)
    limit = get_settings().max_active_exceptions_per_rule
    exception_repo = PolicyExceptionRepository(session)
    if await exception_repo.count_active_for_rule(rule.id, now=now) >= limit:
        raise ActiveExceptionLimitExceededError(limit)

    exception = PolicyException(
        organization_id=organization_id,
        rule_id=rule.id,
        supplier_id=supplier_id,
        contract_version_id=contract_version_id,
        justification=justification,
        approver_role=rule.approver_role,
        granted_by=actor_id,
        valid_until=valid_until,
    )
    exception_repo.add(exception)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="policy.exception_granted",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "policy_exception_id": str(exception.id),
            "rule_id": str(rule.id),
            "rule_key": rule.rule_key,
            "supplier_id": str(supplier_id) if supplier_id is not None else None,
            "contract_version_id": str(contract_version_id)
            if contract_version_id is not None
            else None,
            "approver_role": rule.approver_role,
            "valid_until": valid_until.isoformat(),
        },
    )

    await session.commit()
    await session.refresh(exception)
    return exception


async def list_exceptions_for_rule(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> list[PolicyException]:
    """Read-only; raises the same `PolicyNotFoundError`/`PolicyVersionNotFoundError`/
    `RuleNotFoundError` as `grant_exception` if the rule isn't this organization's."""
    rule = await rule_service.get_rule(
        session,
        organization_id=organization_id,
        policy_id=policy_id,
        version_id=version_id,
        rule_id=rule_id,
    )
    return await PolicyExceptionRepository(session).list_by_rule(
        rule.id, organization_id=organization_id
    )
