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

from app.core.db import Base
from app.policies.domain.constants import PolicyStatus, PolicyVersionStatus
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
    any further change to a mutable field on a frozen row, regardless of which code path
    attempts it (service, a future second API route, a script) -- not just the route this
    epic ships.
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
