import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.approvals.domain.constants import ApprovalRequestStatus
from app.approvals.domain.errors import ApprovalRequestAlreadyResolvedError
from app.core.db import Base


class ApprovalWorkflow(Base):
    """The organization-configured routing template for a given severity tier
    (docs/03-domain/domain-model.md "ApprovalWorkflow"; ADR-006; FEATURE-6.1).

    Keyed by (`organization_id`, `trigger_condition`) -- a severity tier
    (`app.approvals.domain.constants.SeverityTier`), **not** a per-rule lookup: per
    docs/03-domain/approvals.md's own routing table, a HIGH-tier REVIEW always runs the
    full configured chain regardless of which specific rule triggered it. `steps` is the
    ordered list of approver-role strings (domain-model.md invariant: "at least one step
    required" -- enforced in `workflow_service`, since this is organization-configured
    data, not something this model can validate contents of on its own beyond "non-empty
    list", which the application layer that creates/edits rows is responsible for).

    Not versioned in v1 (domain-model.md: "future item if historical reproducibility of
    *workflow configuration*... becomes required") -- editing an active row does not
    retroactively change any already-instantiated `ApprovalRequest` (that one keeps the
    `approver_role` it was created with); only *not-yet-instantiated* later steps in a
    chain use whatever this row's `steps` currently says, since there is no snapshot
    mechanism for workflow configuration itself.
    """

    __tablename__ = "approval_workflows"
    __table_args__ = (
        Index(
            "ix_approval_workflows_org_trigger_condition",
            "organization_id",
            "trigger_condition",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    # Plain severity-tier string (app.approvals.domain.constants.SeverityTier's values),
    # never a cross-context enum import -- see that module's docstring.
    trigger_condition: Mapped[str] = mapped_column(String(20))
    # Ordered list of approver-role strings, mirroring ComplianceReview.policy_version_ids'
    # JSON-list convention for portability with the sqlite-backed test suite.
    steps: Mapped[list[str]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ApprovalRequest(Base):
    """One concrete instance of a human approval step for a `ComplianceReview` with a
    `REVIEW` outcome (docs/03-domain/domain-model.md "ApprovalRequest"; APR-001/APR-002;
    BR-APR-001/BR-APR-002/BR-APR-003; FEATURE-6.1/6.2).

    ## Design decision: `approval_workflow_id` (beyond domain-model.md's literal column
    list)
    The epic brief's column list is `id, organization_id, compliance_review_id,
    approver_role, step_number, status, justification, resolved_by, resolved_at,
    requested_at, timestamps` -- it does not mention a workflow reference. But resolving
    one step (`approval_service.approve_request`) must know whether more steps remain and,
    if so, which `approver_role` the next one needs -- information that lives on the
    `ApprovalWorkflow` the chain was instantiated from, not on this row's own listed
    columns. Re-deriving "the workflow for this severity tier" at resolution time would
    also silently let an admin's *later* edit to the organization's `ApprovalWorkflow`
    change an *in-progress* chain's remaining steps, which is a defensible but
    undocumented behavior either way (`ApprovalWorkflow` is "not versioned in v1" per
    domain-model.md, so there is no snapshot to fall back on). Storing the concrete
    `approval_workflow_id` the chain actually started from is the smallest schema addition
    that makes "is there a next step, and what role does it need" a direct, unambiguous
    lookup rather than a re-derivation -- see `approval_service.approve_request`.

    Immutable once resolved (`status != "pending"`) -- the `@validates` guard below
    mirrors `app.policies.infrastructure.models.Rule._guard_frozen`'s exact pattern,
    guarding every field a resolution touches (`status`/`justification`/`resolved_by`/
    `resolved_at`). As with `Rule`, this is a Python-level, defense-in-depth guard on top
    of the application layer's own explicit `status != PENDING` check
    (`approval_service.approve_request`/`reject_request`) -- not a database constraint,
    and not a guard against bulk/raw-SQL updates.
    """

    __tablename__ = "approval_requests"
    __table_args__ = (
        Index(
            "ix_approval_requests_org_review",
            "organization_id",
            "compliance_review_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    compliance_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compliance_reviews.id"), index=True
    )
    approval_workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_workflows.id"), index=True
    )
    approver_role: Mapped[str] = mapped_column(String(50))
    step_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalRequestStatus.PENDING.value)
    # Non-empty required on reject, optional on approve (approval_service) -- the model
    # itself does not enforce non-emptiness, since it has no way to tell which
    # transition is in progress; see `approval_service.reject_request`.
    justification: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @validates("status", "justification", "resolved_by", "resolved_at")
    def _guard_resolved(self, key: str, value: Any) -> Any:
        # Mirrors Rule._guard_frozen exactly, substituting "status is already a terminal
        # value" for that model's separate `is_frozen` flag -- there is no equivalent
        # separate flag here, `status` itself is the signal. Resolving a request legally
        # changes several of these fields in one call (approval_service sets
        # justification/resolved_by/resolved_at *before* finally setting status to the
        # terminal value last) -- as long as `status` is still "pending" at the moment
        # each field is assigned, every assignment in that single resolution is allowed;
        # only a *second*, later attempt to touch any of these fields -- after `status`
        # has already become non-pending -- is refused.
        current_status = getattr(self, "status", None)
        if (
            current_status is not None
            and current_status != ApprovalRequestStatus.PENDING.value
            and getattr(self, key) != value
        ):
            raise ApprovalRequestAlreadyResolvedError()
        return value


class Decision(Base):
    """The final, packaged compliance outcome for a `ComplianceReview`
    (docs/03-domain/domain-model.md "Decision"; DEC-001/DEC-002; BR-DEC-001/BR-DEC-003/
    BR-DEC-004; FEATURE-6.3).

    One-to-one with `ComplianceReview` *in this round* -- `compliance_review_id` is
    indexed but deliberately **not** given a unique constraint: FEATURE-6.4
    (re-evaluation, explicitly out of scope this round) will eventually let a new
    `Decision` supersede an old one for the *same* review via `supersedes_decision_id`,
    at which point a hard DB-level uniqueness constraint on `compliance_review_id` would
    have to be dropped again. Nothing in this round's code path ever creates a second
    `Decision` for one review (no re-evaluation trigger exists yet), so the invariant
    holds in practice without a DB constraint enforcing it prematurely.

    `overridden`/`override_justification` are the one documented exception to "never
    edited in place" (domain-model.md's invariant is about *re-evaluation*, not override;
    BR-DEC-003 explicitly models override as an in-place status change with mandatory
    justification, never a silent one) -- see `decision_service.override_decision`.
    """

    __tablename__ = "decisions"
    __table_args__ = (
        Index("ix_decisions_org_review", "organization_id", "compliance_review_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    compliance_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compliance_reviews.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # FEATURE-6.4 (deferred, out of scope this round): nothing populates this column yet.
    supersedes_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("decisions.id"), default=None
    )
    overridden: Mapped[bool] = mapped_column(default=False)
    override_justification: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
