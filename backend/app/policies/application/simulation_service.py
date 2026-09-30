"""Simulation / dry-run (#61; docs/03-domain/policy-engine.md "Simulation / dry-run").

## Scope call (documented per this epic's own working method, matching prior epics'
frontend scope calls)

Issue #61 is a FEATURE with no child STORY in Plane for this specific capability; #62
("compliance review results screen") is explicitly out of scope (Phase-5-dependent). This
module is the FEATURE's real content: it runs a `PolicyVersion`'s rules (draft or
published) against one or more existing `ContractVersion`s and returns a per-rule +
aggregate-preview result, with these explicit properties:

- **No side effects on the real domain.** No `ComplianceReview`/`RuleEvaluation`/
  `Decision` row is created (those tables don't exist yet -- Phase 5/EPIC-5 owns them).
- **No real domain event.** `emit_audit_event` (the mechanism that would make this
  indistinguishable from a real evaluation in the audit trail) is never called here.
  Instead, each simulation run emits one Python log record at `INFO` on a logger name
  that unambiguously marks it as a simulation (`jurisense.policies.simulation`), for "the
  policy author's benefit" per the doc -- never mistakable for
  `policy.version_published`/a future `compliance.review_completed` audit event.
- **Works against a draft OR published PolicyVersion.** A compliance team needs to answer
  "if we tighten this rule, how many active contracts would suddenly fail?" *before*
  publishing (the doc's own example), so a draft version's (possibly still-being-edited)
  rules are simulatable too, not only a published version's frozen ones.
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.application import policy_service
from app.policies.application.context_builder import build_context_for_contract_version
from app.policies.application.evaluation_service import (
    AggregatePreview,
    RuleEvaluationResult,
    aggregate_preview,
    evaluate_policy_version,
)
from app.policies.infrastructure.repositories import RuleRepository

logger = logging.getLogger("jurisense.policies.simulation")


@dataclass(frozen=True)
class ContractSimulationResult:
    contract_version_id: str
    rule_evaluations: list[RuleEvaluationResult]
    aggregate: AggregatePreview


@dataclass(frozen=True)
class SimulationResult:
    policy_id: str
    policy_version_id: str
    version_number: int
    version_status: str
    contract_results: list[ContractSimulationResult]


async def run_simulation(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    policy_id: uuid.UUID,
    version_id: uuid.UUID,
    contract_version_ids: list[uuid.UUID],
) -> SimulationResult:
    version = await policy_service.get_version(
        session, organization_id=organization_id, policy_id=policy_id, version_id=version_id
    )
    rules = await RuleRepository(session).list_by_version(version.id)

    contract_results: list[ContractSimulationResult] = []
    for contract_version_id in contract_version_ids:
        context = await build_context_for_contract_version(
            session, organization_id=organization_id, contract_version_id=contract_version_id
        )
        rule_evaluations = evaluate_policy_version(rules, context)
        aggregate = aggregate_preview(rule_evaluations)
        contract_results.append(
            ContractSimulationResult(
                contract_version_id=str(contract_version_id),
                rule_evaluations=rule_evaluations,
                aggregate=aggregate,
            )
        )

    # Simulation-distinguishing log, per this module's docstring -- deliberately not
    # `emit_audit_event`: this run affects nothing real and must never be mistaken for one
    # that did.
    logger.info(
        "SIMULATION policy_id=%s policy_version_id=%s (status=%s) actor_id=%s "
        "contract_version_count=%d results=%s",
        policy_id,
        version.id,
        version.status,
        actor_id,
        len(contract_version_ids),
        [
            {"contract_version_id": r.contract_version_id, "aggregate_status": r.aggregate.status}
            for r in contract_results
        ],
    )

    return SimulationResult(
        policy_id=str(policy_id),
        policy_version_id=str(version.id),
        version_number=version.version_number,
        version_status=version.status,
        contract_results=contract_results,
    )
