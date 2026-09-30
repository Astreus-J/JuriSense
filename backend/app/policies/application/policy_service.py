"""Policy container + PolicyVersion lifecycle (#57). Creating a Policy always creates its
first draft PolicyVersion in the same operation -- a Policy with zero versions has
nowhere for Rules to live (docs/03-domain/policy-engine.md: "A Rule is created/edited
only inside a draft PolicyVersion")."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.audit_service import emit_audit_event
from app.policies.domain.constants import PolicyVersionStatus
from app.policies.domain.errors import (
    PolicyNotFoundError,
    PolicyVersionConflictError,
    PolicyVersionNotFoundError,
)
from app.policies.infrastructure.models import Policy, PolicyVersion, Rule
from app.policies.infrastructure.repositories import (
    PolicyRepository,
    PolicyVersionRepository,
    RuleRepository,
)


async def create_policy(
    session: AsyncSession, *, organization_id: uuid.UUID, actor_id: uuid.UUID, name: str
) -> tuple[Policy, PolicyVersion]:
    policy = Policy(organization_id=organization_id, name=name)
    PolicyRepository(session).add(policy)
    await session.flush()

    version = PolicyVersion(
        policy_id=policy.id, version_number=1, status=PolicyVersionStatus.DRAFT.value
    )
    PolicyVersionRepository(session).add(version)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="policy.created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={"policy_id": str(policy.id), "name": policy.name},
    )

    await session.commit()
    await session.refresh(policy)
    await session.refresh(version)
    return policy, version


async def list_policies(session: AsyncSession, *, organization_id: uuid.UUID) -> list[Policy]:
    return await PolicyRepository(session).list_by_organization(organization_id)


async def get_policy(
    session: AsyncSession, *, organization_id: uuid.UUID, policy_id: uuid.UUID
) -> Policy:
    policy = await PolicyRepository(session).get_by_id_and_organization(policy_id, organization_id)
    if policy is None:
        raise PolicyNotFoundError()
    return policy


async def list_versions(
    session: AsyncSession, *, organization_id: uuid.UUID, policy_id: uuid.UUID
) -> list[PolicyVersion]:
    await get_policy(session, organization_id=organization_id, policy_id=policy_id)
    return await PolicyVersionRepository(session).list_by_policy(policy_id)


async def get_version(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PolicyVersion:
    await get_policy(session, organization_id=organization_id, policy_id=policy_id)
    version = await PolicyVersionRepository(session).get_by_id_and_policy(version_id, policy_id)
    if version is None:
        raise PolicyVersionNotFoundError()
    return version


async def create_draft_version(
    session: AsyncSession, *, organization_id: uuid.UUID, actor_id: uuid.UUID, policy_id: uuid.UUID
) -> PolicyVersion:
    """BR-POL-001's "editing always produces a new version via copy-modify": a new draft
    PolicyVersion is created, its Rules copy-modified (fresh, unfrozen `Rule` rows) from
    whichever version is currently `is_current` -- or empty, if the Policy has never been
    published yet."""
    policy = await get_policy(session, organization_id=organization_id, policy_id=policy_id)
    version_repo = PolicyVersionRepository(session)
    rule_repo = RuleRepository(session)

    current = await version_repo.get_current_by_policy(policy.id)
    next_number = await version_repo.get_next_version_number(policy.id)

    new_version = PolicyVersion(
        policy_id=policy.id, version_number=next_number, status=PolicyVersionStatus.DRAFT.value
    )
    version_repo.add(new_version)
    try:
        await session.flush()
    except IntegrityError as exc:
        # QA review (2026-09-30): two concurrent "create draft version" calls computing
        # the same "next" version_number race on uq_policy_version_number -- confirmed
        # empirically to previously surface as an unhandled 500.
        await session.rollback()
        raise PolicyVersionConflictError() from exc

    if current is not None:
        existing_rules = await rule_repo.list_by_version(current.id)
        for rule in existing_rules:
            copied = Rule(
                policy_version_id=new_version.id,
                rule_key=rule.rule_key,
                name=rule.name,
                when=rule.when,
                result_status=rule.result_status,
                severity=rule.severity,
                approver_role=rule.approver_role,
                compiled_presence_cel=rule.compiled_presence_cel,
                compiled_condition_cel=rule.compiled_condition_cel,
            )
            rule_repo.add(copied)

    await emit_audit_event(
        session,
        event_type="policy.version_draft_created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "policy_id": str(policy.id),
            "policy_version_id": str(new_version.id),
            "version_number": new_version.version_number,
            "copied_from_version_id": str(current.id) if current is not None else None,
        },
    )

    await session.commit()
    await session.refresh(new_version)
    return new_version
