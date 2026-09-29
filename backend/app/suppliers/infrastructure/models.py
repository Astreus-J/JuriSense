import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.suppliers.domain.constants import (
    AddressFlag,
    RegistryStatus,
    SupplierCheckStatus,
    SupplierStatus,
)


class Supplier(Base):
    """A third party the organization is evaluating or has contracted
    (docs/03-domain/domain-model.md "Supplier"; SUP-001, BR-SUP-001, BR-SUP-002)."""

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("tax_id", "organization_id", name="uq_supplier_tax_id_organization"),
        Index("ix_suppliers_organization_status", "organization_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    legal_name: Mapped[str] = mapped_column(String(255))
    # Jurisdiction-specific identifier (CNPJ digits-only for the Brazil pack).
    tax_id: Mapped[str] = mapped_column(String(32), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(2), default="BR")
    status: Mapped[str] = mapped_column(String(20), default=SupplierStatus.PROSPECT.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SupplierCheck(Base):
    """One immutable, point-in-time verification run (docs/03-domain/domain-model.md
    "SupplierCheck"; SUP-002, SUP-005, BR-SUP-004). Immutable once `completed` or
    `failed` — the repository exposes exactly one completion write, no further update
    path (see `SupplierCheckRepository`)."""

    __tablename__ = "supplier_checks"
    __table_args__ = (Index("ix_supplier_checks_supplier_started_at", "supplier_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SupplierCheckStatus.STARTED.value)
    # Populated at start with the sources this check WILL query (names only); results
    # land in raw_results once each source answers (supplier-compliance.md step 2).
    sources_consulted: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, default=None)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SupplierProfile(Base):
    """Normalized, current-state snapshot of a supplier's registry/corporate data
    (docs/03-domain/domain-model.md "SupplierProfile"; SUP-003, BR-SUP-004). Replaced —
    never mutated — on every successful re-check (`SupplierProfileRepository.replace_current`):
    exactly one row has `is_current=True` per supplier at any time.

    `registry_status`, `sanctions_hit`, `activity_mismatch`, and `address_flag` are the
    four fields `docs/03-domain/policy-engine.md`'s evaluation context consumes directly
    (`supplier.registry_status`, `supplier.sanctions_hit`, ...); everything else here is
    contextual/evidentiary detail Policy & Compliance never parses directly.
    """

    __tablename__ = "supplier_profiles"
    __table_args__ = (
        # Defense-in-depth for the "exactly one current profile per supplier" invariant
        # (application logic in SupplierProfileRepository.replace_current is the primary
        # enforcement — see its docstring for why a cross-dialect partial unique index
        # alone isn't relied on as the sole guard).
        Index(
            "uq_supplier_profiles_one_current",
            "supplier_id",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), index=True)
    source_check_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier_checks.id"))
    is_current: Mapped[bool] = mapped_column(default=True, index=True)

    registry_status: Mapped[str] = mapped_column(String(20), default=RegistryStatus.UNKNOWN.value)
    legal_name: Mapped[str | None] = mapped_column(String(255), default=None)
    corporate_structure: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    responsible_parties: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    cnae_code: Mapped[str | None] = mapped_column(String(20), default=None)
    cnae_description: Mapped[str | None] = mapped_column(String(255), default=None)
    address: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    activity_mismatch: Mapped[bool] = mapped_column(default=False)
    address_flag: Mapped[str] = mapped_column(String(20), default=AddressFlag.UNKNOWN.value)

    # BR-SUP-004 / SUP-004: sticky once true — see SupplierProfileRepository.replace_current
    # for how a routine re-check without a fresh clearance signal can never flip this back
    # to False.
    sanctions_hit: Mapped[bool] = mapped_column(default=False, index=True)
    sanctions_detail: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
