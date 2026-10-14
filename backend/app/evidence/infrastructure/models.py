import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.append_only import register_append_only_guards
from app.core.db import Base


class AuditEvent(Base):
    """Append-only log of every meaningful domain action (docs/03-domain/audit.md).

    `actor_id`/`organization_id` are plain UUID columns, not foreign keys: per
    docs/03-domain/domain-model.md, AuditEvent "references any other entity by id in
    payload" rather than through a DB-level relationship — the audit trail must remain
    resolvable even if the referenced row is later changed or removed. No update or
    delete path exists anywhere for this entity (BR-EVD-003/AUD-002); see
    AuditEventRepository, which exposes only add/get/list. Enforced below the ORM too, by a
    DB trigger rejecting any UPDATE/DELETE (`infrastructure/append_only.py`, #184).
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(default=None, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class EvidencePackage(Base):
    """The complete, hashable bundle backing one `Decision` (docs/03-domain/domain-model.md
    "EvidencePackage"; EVD-001/EVD-002; BR-EVD-001; docs/03-domain/evidence.md).

    One package per Decision, enforced by `uq_evidence_packages_one_per_decision`. A
    superseded Decision keeps its package: nothing here is ever deleted or updated after
    creation -- enforced by a DB trigger, not just application convention
    (`infrastructure/append_only.py`, #184). `merkle_root` is stored for fast reads and
    verification, and is always recomputable from the `Evidence` rows
    (`evidence_package_service.recompute`).
    """

    __tablename__ = "evidence_packages"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_evidence_packages_one_per_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"))
    # FEATURE-8.3: indexed because the public verification page now looks packages up by
    # this column directly (app.evidence.infrastructure.repositories.EvidencePackageRepository
    # .get_by_merkle_root_any_organization) -- previously only ever read, never queried on.
    merkle_root: Mapped[str] = mapped_column(String(64), index=True)
    evidence_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Evidence(Base):
    """One canonical leaf of an `EvidencePackage` (docs/03-domain/domain-model.md "Evidence").

    `payload` holds only hashes, ids, versions and enum values -- never raw contract text or
    personal data (BR-EVD-002). `content_hash` is the leaf hash (domain/merkle.py), stored
    so a recomputation can point at the exact leaf that changed. `(type, ref_id)` is unique
    per package: it is the canonical sort key and the identity of a leaf.
    """

    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("evidence_package_id", "type", "ref_id", name="uq_evidence_one_per_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_packages.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(40))
    ref_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BlockchainAnchor(Base):
    """The on-chain (or transparency-log) reference proving an `EvidencePackage`'s
    `merkle_root` was anchored at a point in time (docs/03-domain/domain-model.md
    "BlockchainAnchor"; `ADR-007`; EVD-003/EVD-004; BR-EVD-002).

    One anchor per package (`uq_blockchain_anchors_one_per_package`) -- a package is either
    not yet submitted, or has exactly one anchor; a failed submission is still the one anchor
    for that package (`status="failed"`), never retried by inserting a second row, so a
    retry's own service-layer logic (not built in this pass -- see FEATURE-8.2's own
    docstring for the manual-only scope call) would need to update this row in place rather
    than create a new one.

    `provider` is `AnchoringProvider.provider_name` (`app.evidence.domain.anchoring`) --
    `"transparency_log"` must always be rendered as a labeled fallback, never presented as a
    blockchain anchor (docs/09-planning/risks.md risk 4's non-negotiable labeling
    requirement). `proof` is `None` until a `get_proof` call populates it; its shape is
    provider-opaque (`AnchorProof.raw`), never inspected by SQL.
    """

    __tablename__ = "blockchain_anchors"
    __table_args__ = (
        UniqueConstraint("evidence_package_id", name="uq_blockchain_anchors_one_per_package"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_packages.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    anchor_ref: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))
    proof: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class EvidenceOverrideAddendum(Base):
    """An anchorable, append-only record of a Decision override, chained onto the
    `EvidencePackage` that already existed (and may already be anchored) for that Decision
    (product decision 2026-10-10, closing #187; docs/03-domain/domain-model.md "Decision"
    invariants).

    `override_decision` can run more than once against the same Decision while it stays
    `ACTIVE`, so a package accumulates one addendum per override, not at most one --
    `sequence_number` orders them and `previous_hash` chains each one's `content_hash` to the
    one before it (`domain/override_addendum.py`), so the sequence itself is tamper-evident.
    Deliberately NOT folded into the package's own Merkle tree (`domain/merkle.py`): that tree
    is sealed the moment the package is created/anchored, and an addendum, by definition,
    happens after that. Wiring a package's addenda into `BlockchainAnchor`/`AnchoringProvider`
    is out of scope here -- today they are stored and readable (via the evidence-package API),
    not yet submitted for anchoring on their own.

    QA/security review (2026-10-10): `evidence_package_service.record_override_addendum` locks
    the parent `EvidencePackage` row (`SELECT ... FOR UPDATE`) before computing the next
    `sequence_number`/`previous_hash`, so two concurrent overrides of the same Decision can
    never compute the same pair -- but that locking is this class's own insurance, not a
    database-level guarantee. `uq_evidence_override_addenda_one_per_sequence` is the backstop:
    even if a future call site ever creates an addendum without taking that lock, two rows
    claiming the same `(evidence_package_id, sequence_number)` can still never both commit.
    """

    __tablename__ = "evidence_override_addenda"
    __table_args__ = (
        UniqueConstraint(
            "evidence_package_id",
            "sequence_number",
            name="uq_evidence_override_addenda_one_per_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    evidence_package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_packages.id"), index=True
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    original_status: Mapped[str] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20))
    justification: Mapped[str] = mapped_column(Text)
    overridden_by: Mapped[uuid.UUID] = mapped_column()
    overridden_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


register_append_only_guards(
    Base.metadata,
    table_names=("audit_events", "evidence_packages", "evidence", "evidence_override_addenda"),
)
