"""Draft-only Rule CRU (#57): create/read/update a Rule inside a draft PolicyVersion.
Every write here runs `rule_dsl.parse_rule_yaml` first -- a syntactically invalid rule,
or one referencing an unknown evaluation-context field, is rejected with
`RuleValidationError` before anything touches the session (never partially saved)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.audit_service import emit_audit_event
from app.policies.application import policy_service
from app.policies.domain.constants import PolicyVersionStatus
from app.policies.domain.errors import (
    DuplicateRuleKeyError,
    PolicyVersionNotDraftError,
    RuleNotFoundError,
)
from app.policies.domain.rule_dsl import ParsedRule, parse_rule_yaml
from app.policies.infrastructure.models import Rule
from app.policies.infrastructure.repositories import RuleRepository


def _require_draft(version_status: str) -> None:
    if version_status != PolicyVersionStatus.DRAFT.value:
        raise PolicyVersionNotDraftError()


async def create_rule(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_yaml: str,
) -> Rule:
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    _require_draft(version.status)

    parsed: ParsedRule = parse_rule_yaml(rule_yaml)

    rule_repo = RuleRepository(session)
    if await rule_repo.get_by_key_and_version(parsed.rule_key, version.id) is not None:
        raise DuplicateRuleKeyError(parsed.rule_key)

    rule = Rule(
        policy_version_id=version.id,
        rule_key=parsed.rule_key,
        name=parsed.name,
        when=parsed.when,
        result_status=parsed.result_status,
        severity=parsed.severity,
        approver_role=parsed.approver_role,
        compiled_presence_cel=parsed.compiled_presence_cel,
        compiled_condition_cel=parsed.compiled_condition_cel,
    )
    rule_repo.add(rule)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="policy.rule_created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "policy_id": str(policy_id),
            "policy_version_id": str(version.id),
            "rule_id": str(rule.id),
            "rule_key": rule.rule_key,
            "result_status": rule.result_status,
            "severity": rule.severity,
        },
    )

    await session.commit()
    await session.refresh(rule)
    return rule


async def list_rules(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
) -> list[Rule]:
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    return await RuleRepository(session).list_by_version(version.id)


async def get_rule(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> Rule:
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    rule = await RuleRepository(session).get_by_id(rule_id)
    if rule is None or rule.policy_version_id != version.id:
        raise RuleNotFoundError()
    return rule


async def update_rule(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    rule_id: uuid.UUID,
    rule_yaml: str,
) -> Rule:
    """Re-validates and re-compiles `rule_yaml` exactly like `create_rule`, then applies
    it to the existing row -- `rule.id` (the UUID PK) is stable across the edit, but
    `rule_key`/`name`/`when`/etc. may all change. `Rule._guard_frozen` (the domain-layer
    BR-POL-001 guard) is the backstop if `version.status` is somehow already `published`
    by the time this write lands; `_require_draft` is the primary, earlier check so the
    caller gets a clear `PolicyVersionNotDraftError` instead of the lower-level
    `PublishedRuleImmutableError`."""
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    _require_draft(version.status)

    rule = await get_rule(
        session,
        organization_id=organization_id,
        policy_id=policy_id,
        version_id=version_id,
        rule_id=rule_id,
    )

    parsed: ParsedRule = parse_rule_yaml(rule_yaml)

    if parsed.rule_key != rule.rule_key:
        rule_repo = RuleRepository(session)
        existing = await rule_repo.get_by_key_and_version(parsed.rule_key, version.id)
        if existing is not None and existing.id != rule.id:
            raise DuplicateRuleKeyError(parsed.rule_key)

    rule.rule_key = parsed.rule_key
    rule.name = parsed.name
    rule.when = parsed.when
    rule.result_status = parsed.result_status
    rule.severity = parsed.severity
    rule.approver_role = parsed.approver_role
    rule.compiled_presence_cel = parsed.compiled_presence_cel
    rule.compiled_condition_cel = parsed.compiled_condition_cel

    await emit_audit_event(
        session,
        event_type="policy.rule_updated",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "policy_id": str(policy_id),
            "policy_version_id": str(version.id),
            "rule_id": str(rule.id),
            "rule_key": rule.rule_key,
        },
    )

    await session.commit()
    await session.refresh(rule)
    return rule
