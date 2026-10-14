import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.append_only import register_append_only_guards
from app.core.db import Base
from app.policies.domain.constants import (
    ComplianceReviewStatus,
    PolicyStatus,
    PolicyVersionStatus,
)
from app.policies.domain.errors import PublishedRuleImmutableError


class Policy(Base):
    """A named, organization-owned collection of Rules (docs/03-domain/domain-model.md
    "Policy"). Container-level metadata only -- the actual rule set lives in its
    PolicyVersions."""

    __tablename__ = "policies"
    __table_args__ = (Index("ix_policies_organization_status", "organization_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=PolicyStatus.DRAFT.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyVersion(Base):
    """An immutable-once-published snapshot of a Policy's rule set
    (docs/03-domain/domain-model.md "PolicyVersion"; BR-POL-001, BR-POL-002).

    Invariant enforcement:
    - BR-POL-001 (rule immutability once published): each owned `Rule` carries its own
      `is_frozen` flag, set exactly once by `publish_service.publish_version` and guarded
      by `Rule`'s own `@validates` hook -- see that model below.
    - BR-POL-002 (exactly one current version per policy): `uq_policy_versions_one_current`
      is a partial unique index on `policy_id` where `is_current`, mirroring
      `SupplierProfile`'s `uq_supplier_profiles_one_current` pattern exactly. As with that
      model, the primary enforcement is the application-level supersede-then-set sequence
      in `publish_service.publish_version`; the index is defense-in-depth against a
      concurrent-publish race.
    """

    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number"),
        Index(
            "uq_policy_versions_one_current",
            "policy_id",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=PolicyVersionStatus.DRAFT.value)
    is_current: Mapped[bool] = mapped_column(default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    published_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rule(Base):
    """One executable condition within a PolicyVersion
    (docs/03-domain/domain-model.md "Rule"; docs/03-domain/policy-engine.md "Rule DSL").

    `id` is a UUID surrogate key (this codebase's consistent convention, e.g.
    `Supplier.id`), even though domain-model.md describes Rule's *conceptual* identity as
    `rule.id` (a business key like "LGPD-001") + `policy_version_id` -- that pairing is
    still enforced, via `uq_rule_key_per_version` below, it just isn't the literal primary
    key column.

    `when`/`result_status`/`severity`/`approver_role` are the parsed DSL fields
    (`app.policies.domain.rule_dsl.ParsedRule`); `compiled_presence_cel`/
    `compiled_condition_cel` are the two CEL expressions the rule-execution engine (#61)
    evaluates (see `rule_dsl`'s module docstring for why two, not one).

    BR-POL-001 (immutable once published) is enforced *at this model*, not only by the
    service layer that normally guards it -- `is_frozen` starts `False` and is flipped to
    `True` exactly once, by `publish_service.publish_version`, in the same transaction
    that publishes the owning `PolicyVersion`. The `@validates` hook below then refuses
    any further change to a mutable field on a frozen row coming through ORM
    instance-attribute assignment (`rule.name = ...`) -- so any future second API route,
    service, or script that loads a `Rule` and mutates it the normal SQLAlchemy way is
    covered, not just `rule_service`'s own routes. It does **not** guard a bulk/raw-SQL
    update (e.g. `session.execute(update(Rule)...)` or a direct `UPDATE rules ...`) that
    bypasses ORM attribute assignment entirely -- `@validates` is a Python-level hook, not
    a database constraint. No code path in this codebase currently does that, so this is a
    documented gap, not a live one; a DB-level trigger would be the defense-in-depth fix
    if a bulk-update path is ever added (tracked as backlog, not yet needed).
    """

    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("policy_version_id", "rule_key", name="uq_rule_key_per_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_versions.id"), index=True
    )
    rule_key: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    when: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_status: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    approver_role: Mapped[str | None] = mapped_column(String(50), default=None)
    compiled_presence_cel: Mapped[str] = mapped_column(Text)
    compiled_condition_cel: Mapped[str] = mapped_column(Text)
    is_frozen: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @validates(
        "rule_key",
        "name",
        "when",
        "result_status",
        "severity",
        "approver_role",
        "compiled_presence_cel",
        "compiled_condition_cel",
    )
    def _guard_frozen(self, key: str, value: Any) -> Any:
        # `getattr(..., False)` handles the brand-new, not-yet-flushed object case, where
        # `is_frozen`'s column default hasn't been applied yet (SQLAlchemy applies
        # `default=` at flush/INSERT time, not at `__init__`).
        if getattr(self, "is_frozen", False) and getattr(self, key) != value:
            raise PublishedRuleImmutableError()
        return value


class PolicyException(Base):
    """A time-boxed, approver-signed waiver of one `Rule` for one Supplier or
    ContractVersion (docs/03-domain/policy-engine.md "Exceptions & manual overrides";
    #120, STORY-4.4.2).

    Scope: only a REVIEW-tier `Rule` (non-null `approver_role`) can be targeted -- a
    BLOCK-tier rule's `approver_role` is structurally `None` (`rule_dsl`'s own DSL
    validation), so there is no single role an exception could ever attribute itself to
    for one; see `RuleNotEligibleForExceptionError`. Targets exactly one of `supplier_id`/
    `contract_version_id` (never both, never neither) -- validated in
    `exception_service.grant_exception`, not by a DB CHECK constraint, matching this
    codebase's existing precedent of enforcing exactly-one-of invariants at the
    application layer rather than the schema (no CHECK-constraint precedent exists
    anywhere else in this codebase either).

    `approver_role` here is a snapshot of the waived `Rule.approver_role` at grant time --
    never user-supplied -- so the exception's own record of "whose sign-off this was"
    survives even if the rule is later edited in a new draft version (BR-POL-001's
    copy-modify can change a copied rule's `approver_role` going forward; this row
    continues to describe the exact rule+role pairing that was actually waived).

    This is a documented override INPUT to evaluation (`evaluation_service.evaluate_rule`
    checks for an applicable active exception before running any CEL at all), never a
    mutation of the `Rule` row itself -- `Rule.when`/`compiled_*_cel` are untouched.

    Immutable once created (no update/delete method exists on
    `PolicyExceptionRepository`) -- an exception that should no longer apply is left to
    expire via `valid_until`, never edited or revoked in place; this mirrors
    `RuleEvaluation`/`Risk`'s own append-only contract and keeps "what exception was
    active when rule X was evaluated" always reconstructable after the fact.
    """

    __tablename__ = "policy_exceptions"
    __table_args__ = (
        Index("ix_policy_exceptions_rule_supplier", "rule_id", "supplier_id"),
        Index("ix_policy_exceptions_rule_contract_version", "rule_id", "contract_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.id"), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), default=None
    )
    contract_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contract_versions.id"), default=None
    )
    justification: Mapped[str] = mapped_column(Text)
    approver_role: Mapped[str] = mapped_column(String(50))
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceReview(Base):
    """One evaluation run of a `ContractVersion` against every currently-published
    `PolicyVersion` in the organization (docs/03-domain/domain-model.md
    "ComplianceReview"; ADR-010; Phase 5/EPIC-5, #123).

    ## Design decision: multi-policy pooling (#123 -- resolving an open question)
    `docs/03-domain/domain-model.md`'s `Policy` entity states no one-org-one-active-policy
    constraint anywhere. Rather than force a policy-selection step onto the triggering
    user (which would let a reviewer silently skip e.g. a "Data Privacy" policy by only
    picking "Vendor Compliance"), `compliance_review_service.trigger_review` pools the
    Rules of EVERY currently-published `PolicyVersion` in the organization into one
    `ComplianceReview` -- one explainable APPROVE/REVIEW/BLOCK gate per contract, matching
    the product's own "one explainable status" framing (ADR-010's Consequences: "simple
    enough to explain to a customer's Legal/Compliance team in one sentence").

    Consequence for this model: `policy_version_id` (singular, per domain-model.md's
    literal attribute list) cannot hold the true relationship once more than one
    `PolicyVersion` contributes rules to a review -- `policy_version_ids` (plural, a JSON
    array snapshot, mirroring `SupplierCheck.sources_consulted`'s existing
    JSON-array-of-identifiers pattern) replaces it below. The involved `PolicyVersion` set
    is independently reconstructable from the persisted
    `RuleEvaluation.rule_id -> Rule.policy_version_id` chain too; this column exists for
    fast, join-free "which policies applied" reads, not as the sole record of the fact.

    Immutable once its `status` leaves `IN_PROGRESS` (BR-CMP-003's append-only spirit,
    applied to the review record itself, not just `RuleEvaluation`) -- see
    `ComplianceReviewStatus`'s docstring for why a persisted row is always already
    terminal in practice (rule evaluation is synchronous/in-process, not an async step).
    """

    __tablename__ = "compliance_reviews"
    __table_args__ = (
        Index(
            "ix_compliance_reviews_org_contract_version",
            "organization_id",
            "contract_version_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract_versions.id"), index=True
    )
    # Snapshot of every currently-published PolicyVersion pooled into this review at
    # trigger time -- see the multi-policy-pooling design decision above. Stored as
    # strings (not a Postgres UUID[] array) to stay portable with the sqlite-backed test
    # suite, matching this codebase's existing JSON-list-of-ids convention.
    policy_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(
        String(20), default=ComplianceReviewStatus.IN_PROGRESS.value
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # FEATURE-6.4 (BR-DEC-002): set when this review is a re-evaluation of an earlier
    # Decision; the Decision it produces carries the same link. Null for first-time reviews.
    # use_alter: this FK closes a cycle (decisions.compliance_review_id -> compliance_reviews),
    # which SQLAlchemy can only sort by emitting the constraint as a separate ALTER.
    supersedes_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "decisions.id",
            name="fk_compliance_reviews_supersedes_decision_id",
            use_alter=True,
        ),
        index=True,
        default=None,
    )


class RuleEvaluation(Base):
    """The result of evaluating one `Rule` within a `ComplianceReview`
    (docs/03-domain/domain-model.md "RuleEvaluation"; ADR-010; Phase 5/EPIC-5, #125/#126).

    Append-only by construction -- `RuleEvaluationRepository` exposes only `add`/`get`/
    `list`, no update or delete method exists anywhere on that class, mirroring
    `AuditEventRepository` exactly (BR-CMP-003: "never edited or deleted, including by a
    [future] override").

    `rule_key`/`rule_name` are denormalized snapshots of the evaluated `Rule`'s own fields
    at evaluation time -- harmless to duplicate since a published `Rule` is frozen
    (BR-POL-001) and can never drift from this snapshot; they exist so the read-model
    (`GET /compliance/reviews/{id}`) never needs a join back to `rules` just to render a
    label. `evidence_refs` is the concrete mechanism behind the product's "WHY, EVIDENCE,
    POLICY, SOURCE" explainability principle -- see
    `app.policies.application.compliance_review_service` for how it's populated from the
    rule's referenced context paths, never left as a placeholder.
    """

    __tablename__ = "rule_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    compliance_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compliance_reviews.id"), index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rules.id"), index=True)
    rule_key: Mapped[str] = mapped_column(String(50))
    rule_name: Mapped[str] = mapped_column(String(255))
    outcome: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    approver_role: Mapped[str | None] = mapped_column(String(50), default=None)
    rationale: Mapped[str] = mapped_column(Text)
    # #120: set only when `outcome == EXEMPTED` -- the `PolicyException` that caused this
    # rule to be waived rather than CEL-evaluated. `None` for every other outcome.
    exception_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_exceptions.id"), default=None
    )
    # Each entry traces one referenced evaluation-context path back to the evidence that
    # produced it -- a Contract extraction-field provenance (document_id/page/text_span)
    # or a Supplier evidence-port reference (supplier_id/supplier_profile_id/
    # supplier_check_id). See `compliance_review_service._build_evidence_refs`.
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Risk(Base):
    """A named risk finding surfaced during review (docs/03-domain/domain-model.md
    "Risk"; Phase 5/EPIC-5, #125).

    ## Design decision: Risk provenance (#125 -- resolving an open question)
    domain-model.md notes Risk "may or may not map 1:1" to a `RuleEvaluation`. This
    epic's only risk source is rule evaluation itself, so `compliance_review_service`
    derives exactly one `Risk` row per `RuleEvaluation` whose `outcome` is `REVIEW` or
    `BLOCK` (a `PASS`/`NOT_APPLICABLE` rule represents the *absence* of a finding, not
    one) -- a defensible 1:1 mapping for now. The schema itself does not assume 1:1: `Risk`
    has its own independent FK to `ComplianceReview`, not to `RuleEvaluation`, so a future
    non-rule-derived risk source (e.g. an anomaly detector) can insert additional `Risk`
    rows with no `RuleEvaluation` counterpart, exactly as domain-model.md anticipates.

    Immutable once created -- `RiskRepository` exposes only `add`/`list`, no update/delete.

    ## `policy_id` (#179, 2026-10-12)
    `category` alone is `rule_key`, which `uq_rule_key_per_version` only guarantees unique
    PER `PolicyVersion` -- two different, independently-authored Policies in the same
    organization can legitimately reuse the same `rule_key` string for unrelated rules (the
    pooling `compliance_review_service.execute_review` already does across every currently-
    published Policy makes this a real, if rare, authoring collision, not a hypothetical
    one). `policy_id` disambiguates without changing `category`'s existing meaning/format,
    so every existing consumer that reads `category` as the human-readable rule_key is
    unaffected; a caller that needs to tell two same-`category` Risk rows apart now can.
    """

    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    compliance_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compliance_reviews.id"), index=True
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policies.id"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Security audit (2026-10-12): `compliance_reviews`, `rule_evaluations`, and `policy_exceptions`
# are append-only by repository convention already (no update/delete method exposed on any of
# their repositories) -- same gap #184 closed for the Evidence & Audit tables, now closed here
# too. Scoped to exactly these three, not every table in this file: `policies`/`policy_versions`/
# `rules` are genuinely mutable by design while a `PolicyVersion` is still `draft` (rule_service's
# own create/update routes), and `Rule` already has its own ORM-level `@validates` guard
# (`_guard_frozen`) for the one point it becomes immutable (publish) rather than a DB trigger,
# since it is conditionally mutable, not append-only from creation. `risks` is not included
# either: no code path updates a `Risk` row either, but it was not part of this audit's finding
# and is left for a follow-up pass rather than added speculatively.
register_append_only_guards(
    Base.metadata,
    table_names=("compliance_reviews", "rule_evaluations", "policy_exceptions"),
)
