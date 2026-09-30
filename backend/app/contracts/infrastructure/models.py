import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.contracts.domain.constants import ContractStatus, ContractVersionStatus, DocumentStatus
from app.contracts.domain.errors import InvalidClauseProvenanceError
from app.core.db import Base


class Document(Base):
    """Any uploaded file (docs/03-domain/domain-model.md "Document"; CON-001, SEC-003).
    Immutable once created: `content_hash` is computed once at upload and never
    recomputed (domain-model.md invariant) -- there is no update path in
    `DocumentRepository` for either field."""

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_organization_hash", "organization_id", "content_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    # SHA-256 hex digest, computed once at upload (never recomputed) -- this is what
    # later anchors into the EvidencePackage (docs/03-domain/evidence.md).
    content_hash: Mapped[str] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.UPLOADED.value)
    failure_reason: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Contract(Base):
    """The logical agreement with a Supplier, spanning many versions
    (docs/03-domain/domain-model.md "Contract"; BR-CON-001)."""

    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_organization_supplier", "organization_id", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    # BR-CON-001: a Contract belongs to exactly one Supplier -- enforced by never
    # allowing this to change after creation (no update path in ContractRepository).
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    contract_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default=ContractStatus.DRAFT.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContractVersion(Base):
    """One immutable snapshot of a contract's text/terms + AI-extracted structured data
    (docs/03-domain/domain-model.md "ContractVersion"; BR-CON-002, BR-CON-003). Never
    edited in place: a new negotiation round always inserts a new row
    (`ContractVersionRepository` exposes no field-level update beyond the
    status/extracted_data transition the extraction pipeline itself performs once,
    on the row it just created)."""

    __tablename__ = "contract_versions"
    __table_args__ = (
        Index("ix_contract_versions_contract_number", "contract_id", "version_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=ContractVersionStatus.EXTRACTED.value)
    # Schema per docs/05-ai/structured-extraction.md (ExtractionEnvelope, minus the
    # envelope-level metadata already captured by this row's own columns).
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # BR-CON-003: the minimum confidence across every extracted field (contract-compliance.md's
    # "one weak field... cannot be masked by high confidence on unrelated fields" rule) --
    # never an average. Null while extraction has not yet run/failed.
    extraction_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    extraction_failure_reason: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Clause(Base):
    """One AI-identified, citable clause within a ContractVersion
    (docs/03-domain/domain-model.md "Clause"; CON-004, BR-CON-004). Immutable once
    created -- `ClauseRepository` exposes no update method at all.

    BR-CON-004 ("a clause without provenance cannot be used as evidence") is enforced at
    *construction* time below, not merely via nullable-column-plus-later-validation: a
    `Clause` missing `page` or `text_span` cannot come into existence as a Python object
    in the first place, which is stronger than a NOT NULL column (that only stops a bad
    row from being flushed to the database, not from existing transiently in memory and
    being handed around/serialized before that flush happens).
    """

    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    contract_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contract_versions.id"), index=True
    )
    clause_type: Mapped[str] = mapped_column(String(50))
    page: Mapped[int] = mapped_column(Integer)
    text_span: Mapped[dict[str, int]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    text_excerpt: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs: Any) -> None:
        _validate_clause_provenance(page=kwargs.get("page"), text_span=kwargs.get("text_span"))
        super().__init__(**kwargs)


def _validate_clause_provenance(*, page: Any, text_span: Any) -> None:
    """The construction-time guard itself, factored out so it can be unit-tested (and
    reused) independently of SQLAlchemy's `__init__` plumbing (BR-CON-004)."""
    if page is None:
        raise InvalidClauseProvenanceError(
            "Clause requires a non-null 'page' at construction time (BR-CON-004)"
        )
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise InvalidClauseProvenanceError(
            "Clause 'page' must be a positive integer (BR-CON-004)"
        )
    if not isinstance(text_span, dict) or "start" not in text_span or "end" not in text_span:
        raise InvalidClauseProvenanceError(
            "Clause requires a non-null 'text_span' with 'start'/'end' at construction "
            "time (BR-CON-004)"
        )
    start, end = text_span.get("start"), text_span.get("end")
    if start is None or end is None:
        raise InvalidClauseProvenanceError(
            "Clause 'text_span.start'/'text_span.end' must not be null (BR-CON-004)"
        )
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
        raise InvalidClauseProvenanceError(
            "Clause 'text_span' must have non-negative integer 'start' <= 'end' (BR-CON-004)"
        )
