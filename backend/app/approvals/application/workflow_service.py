"""`ApprovalWorkflow` configuration and default seeding (FEATURE-6.1, APR-001/APR-003;
docs/03-domain/approvals.md "ApprovalWorkflow configuration").
"""

import uuid

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
_DEFAULT_WORKFLOW_STEPS: dict[str, list[str]] = {
    SeverityTier.MEDIUM.value: ["legal"],
    SeverityTier.HIGH.value: ["compliance", "legal", "director"],
    SeverityTier.CRITICAL.value: ["compliance", "legal", "director"],
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


async def get_workflow_for_tier(
    session: AsyncSession, *, organization_id: uuid.UUID, trigger_condition: str
) -> ApprovalWorkflow | None:
    """Returns `None` (never raises) when no workflow is configured for this tier --
    the caller (`approval_service.create_approval_requests_for_review`) decides what that
    means (`NoApprovalWorkflowConfiguredError`)."""
    return await ApprovalWorkflowRepository(session).get_by_organization_and_trigger(
        organization_id, trigger_condition
    )
