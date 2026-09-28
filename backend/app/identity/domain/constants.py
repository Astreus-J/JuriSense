"""Access roles (RBAC, ADR-003), system modules, and commercial plans."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """The 10 compliance roles defined in ADR-003 / docs/03-domain/domain-model.md."""

    ADMIN = "admin"
    PROCUREMENT = "procurement"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    PRIVACY = "privacy"
    SECURITY = "security"
    FINANCE = "finance"
    APPROVER = "approver"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    PENDING = "pending"


class Plan(StrEnum):
    """Tier names per docs/02-business/pricing-strategy.md ("Tier hypothesis")."""

    STARTER = "starter"
    BUSINESS = "business"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class PlanLimits:
    """Usage limits per plan; None means unlimited.

    Dimensions follow docs/02-business/pricing-strategy.md's limit-dimension table:
    - user_limit: seats.
    - supplier_limit: suppliers under active management (replaces the legacy
      "active legal cases" dimension, which has no meaning in a compliance platform).
    - storage_limit_gb: object storage for documents/evidence.
    - ai_execution_limit: AI executions per month (extraction/classification calls).

    The exact numeric caps are explicitly TBD per pricing-strategy.md pending customer
    discovery; the values in PLAN_LIMITS below carry over the magnitudes from the
    pre-pivot plan table as placeholders (only their meaning changed), not validated
    business numbers.
    """

    user_limit: int | None
    supplier_limit: int | None
    storage_limit_gb: int | None
    ai_execution_limit: int | None


PLAN_LIMITS: dict[Plan, PlanLimits] = {
    Plan.STARTER: PlanLimits(1, 250, 15, 50),
    Plan.BUSINESS: PlanLimits(5, 1250, 75, 250),
    Plan.GROWTH: PlanLimits(20, 5000, 300, 1000),
    Plan.ENTERPRISE: PlanLimits(None, None, None, None),
}


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MembershipStatus(StrEnum):
    """Membership lifecycle per docs/03-domain/domain-model.md: invited → active → revoked."""

    INVITED = "invited"
    ACTIVE = "active"
    REVOKED = "revoked"


class Module(StrEnum):
    """Module vocabulary per ADR-003 (replaces the legacy legal-ERP module set)."""

    SUPPLIERS = "suppliers"
    CONTRACTS = "contracts"
    POLICIES = "policies"
    COMPLIANCE_REVIEWS = "compliance_reviews"
    APPROVALS = "approvals"
    EVIDENCE = "evidence"
    INTEGRATIONS = "integrations"
    ORGANIZATION_SETTINGS = "organization_settings"
