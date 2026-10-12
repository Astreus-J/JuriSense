"""`ApprovalWorkflow` configuration and default seeding (FEATURE-6.1, APR-001/APR-003;
docs/03-domain/approvals.md "ApprovalWorkflow configuration").
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.domain.constants import SeverityTier
from app.approvals.infrastructure.models import ApprovalWorkflow
from app.approvals.infrastructure.repositories import ApprovalWorkflowRepository

# docs/03-domain/approvals.md's own routing table (the product's documented default,
# organization-editable thereafter): MEDIUM -> single-step Legal; HIGH -> the full
# Compliance -> Legal -> Director chain. The docs don't give CRITICAL its own row -- this
# reuses HIGH's chain as a reasonable, documented default (see
# `seed_default_workflows`'s docstring). LOW is intentionally left unconfigured: per the
# routing table, a LOW-severity REVIEW outcome is an undocumented edge case the product
# doesn't define a workflow for.
#
# Product decision (2026-10-12, #181): the chain's final step is seeded as "approver", the
# real `app.identity.domain.constants.Role` value -- not the string "director", which
# never existed as an actual RBAC role (rbac.py's own docstring already called `approver`
# "the generic Director/Approver persona," but this seed never matched it). "Director"
# stays the product's persona-facing LABEL for this step wherever it's displayed to a
# user; it is not, and was never meant to be, a distinct technical role with its own
# permission grid.
_DEFAULT_WORKFLOW_STEPS: dict[str, list[str]] = {
    SeverityTier.MEDIUM.value: ["legal"],
    SeverityTier.HIGH.value: ["compliance", "legal", "approver"],
    SeverityTier.CRITICAL.value: ["compliance", "legal", "approver"],
}


async def seed_default_workflows(
    session: AsyncSession, *, organization_id: uuid.UUID
) -> list[ApprovalWorkflow]:
    """Seeds this organization's default `ApprovalWorkflow` rows (medium/high/critical) so
    FEATURE-6.1's routing never has to special-case "no workflow configured" for a
    brand-new organization.

    Called from `app.identity.application.auth_service.register_organization`, right
    after that function seeds the admin's default `ModulePermission` grid
    (`seed_default_permissions`) -- the exact same "bootstrap a sane default at
    organization-creation time" shape. `app.identity` calling into `app.approvals` here is
    a deliberate, documented exception to the usual direction of dependency (Policy &
    Compliance/other contexts call into Approvals & Decisions, not Identity &
    Organizations): organization registration is the one place a brand-new
    organization's full set of sane defaults gets provisioned in one transaction, and
    without this call every organization would need an explicit admin action ("configure
    your approval workflow") before its very first REVIEW-outcome review could be routed
    anywhere -- see this module's own docstring and
    `docs/03-domain/domain-model.md`'s `ApprovalWorkflow` invariant ("at least one step
    required").

    Does not commit -- the caller (`register_organization`) commits once at the end of its
    own use case, matching every other `repository.add()` call in this codebase.
    """
    repository = ApprovalWorkflowRepository(session)
    workflows = []
    for trigger_condition, steps in _DEFAULT_WORKFLOW_STEPS.items():
        workflow = ApprovalWorkflow(
            organization_id=organization_id, trigger_condition=trigger_condition, steps=steps
        )
        repository.add(workflow)
        workflows.append(workflow)
    return workflows


@dataclass(frozen=True)
class DirectorStepBackfillResult:
    workflows_checked: int
    workflows_updated: int


async def backfill_director_role_to_approver(session: AsyncSession) -> DirectorStepBackfillResult:
    """Security review (2026-10-12), real finding: #181's fix only changed
    `_DEFAULT_WORKFLOW_STEPS` -- the template `seed_default_workflows` uses for a
    brand-new organization going forward. It never touched any `ApprovalWorkflow` row
    already persisted for an organization registered *before* that fix, each of which
    still has `"director"` baked into its `steps` JSON from the old template. `"director"`
    never matched a real `app.identity.domain.constants.Role` (confirmed by this same
    #181 fix's own docstring), so any such row's HIGH/CRITICAL chain has a step no real
    user can ever resolve -- fails closed (no bypass), but permanently stalls that step.
    Running against the real dev database (2026-10-12) confirmed this is not
    hypothetical: 6 of 9 persisted `ApprovalWorkflow` rows still contained `"director"`.

    One-off remedy, same shape as `app.identity.application.permission_service.
    backfill_missing_module_permissions`: replaces every `"director"` entry with
    `"approver"` in place, for every organization, and commits once (there is no
    per-row failure mode here worth isolating -- a plain list-literal JSON column
    update, not a new-row insert that could collide on a constraint). Idempotent: a
    workflow with no `"director"` step is left untouched and not counted as updated.
    Safe to edit an already-active row in place -- `ApprovalWorkflow`'s own docstring:
    editing a row never retroactively changes an already-instantiated `ApprovalRequest`
    (which keeps the `approver_role` it was created with), only future, not-yet-
    instantiated steps read the row's current `steps`.

    No user-facing route calls this; run manually once to repair organizations that
    predate #181's fix."""
    workflows = list((await session.execute(select(ApprovalWorkflow))).scalars())
    updated = 0
    for workflow in workflows:
        if "director" not in workflow.steps:
            continue
        workflow.steps = ["approver" if step == "director" else step for step in workflow.steps]
        updated += 1
    await session.commit()
    return DirectorStepBackfillResult(workflows_checked=len(workflows), workflows_updated=updated)


async def get_workflow_for_tier(
    session: AsyncSession, *, organization_id: uuid.UUID, trigger_condition: str
) -> ApprovalWorkflow | None:
    """Returns `None` (never raises) when no workflow is configured for this tier --
    the caller (`approval_service.create_approval_requests_for_review`) decides what that
    means (`NoApprovalWorkflowConfiguredError`)."""
    return await ApprovalWorkflowRepository(session).get_by_organization_and_trigger(
        organization_id, trigger_condition
    )
