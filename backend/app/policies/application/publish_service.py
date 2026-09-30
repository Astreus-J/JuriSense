"""Publish action (#58): freezes every Rule in a draft PolicyVersion (BR-POL-001) and
makes it the Policy's one current version (BR-POL-002)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.audit_service import emit_audit_event
from app.policies.application import policy_service
from app.policies.domain.constants import PolicyStatus, PolicyVersionStatus
from app.policies.domain.errors import NoDraftVersionToPublishError, PolicyVersionConflictError
from app.policies.infrastructure.models import PolicyVersion
from app.policies.infrastructure.repositories import PolicyVersionRepository, RuleRepository


async def publish_version(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PolicyVersion:
    policy = await policy_service.get_policy(
        session, organization_id=organization_id, policy_id=policy_id
    )
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    if version.status != PolicyVersionStatus.DRAFT.value:
        raise NoDraftVersionToPublishError()

    version_repo = PolicyVersionRepository(session)
    rule_repo = RuleRepository(session)

    # BR-POL-002: supersede whatever version currently holds `is_current` for this
    # Policy before this one claims it -- same supersede-then-set sequence
    # `SupplierProfileRepository.replace_current` uses, in the same transaction, so the
    # partial unique index (`uq_policy_versions_one_current`) is never even momentarily
    # violated.
    await version_repo.supersede_current(policy.id)

    # BR-POL-001: freeze every Rule this version owns -- from this point on,
    # `Rule._guard_frozen` refuses any further mutation to any of them, regardless of
    # which code path attempts it.
    rules = await rule_repo.list_by_version(version.id)
    rule_repo.freeze(rules)  # synchronous -- pure in-memory attribute assignment

    version.status = PolicyVersionStatus.PUBLISHED.value
    version.is_current = True
    version.published_at = datetime.now(UTC)
    version.published_by = actor_id

    if policy.status == PolicyStatus.DRAFT.value:
        policy.status = PolicyStatus.PUBLISHED.value

    await emit_audit_event(
        session,
        event_type="policy.version_published",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "policy_id": str(policy.id),
            "policy_version_id": str(version.id),
            "version_number": version.version_number,
            "rule_count": len(rules),
        },
    )

    try:
        await session.commit()
    except IntegrityError as exc:
        # QA review (2026-09-30): a concurrent publish of a different draft version of
        # the same Policy can race on uq_policy_versions_one_current -- confirmed
        # empirically to previously surface as an unhandled 500.
        await session.rollback()
        raise PolicyVersionConflictError() from exc
    await session.refresh(version)
    return version
