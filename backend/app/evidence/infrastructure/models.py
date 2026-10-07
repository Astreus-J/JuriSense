import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditEvent(Base):
    """Append-only log of every meaningful domain action (docs/03-domain/audit.md).

    `actor_id`/`organization_id` are plain UUID columns, not foreign keys: per
    docs/03-domain/domain-model.md, AuditEvent "references any other entity by id in
    payload" rather than through a DB-level relationship — the audit trail must remain
    resolvable even if the referenced row is later changed or removed. No update or
    delete path exists anywhere for this entity (BR-EVD-003/AUD-002); see
    AuditEventRepository, which exposes only add/get/list.
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
    creation. `merkle_root` is stored for fast reads and verification, and is always
    recomputable from the `Evidence` rows (`evidence_package_service.recompute`).
    """

    __tablename__ = "evidence_packages"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_evidence_packages_one_per_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"))
    merkle_root: Mapped[str] = mapped_column(String(64))
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
