"""Suppliers vocabulary — see docs/03-domain/domain-model.md ("Supplier", "SupplierCheck",
"SupplierProfile") and docs/03-domain/business-rules.md (BR-SUP-*)."""

from enum import StrEnum


class SupplierStatus(StrEnum):
    """Lifecycle per domain-model.md: prospect -> under_review -> approved|blocked -> inactive."""

    PROSPECT = "prospect"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    BLOCKED = "blocked"
    INACTIVE = "inactive"


class SupplierCheckStatus(StrEnum):
    """Lifecycle per domain-model.md: started -> completed|failed. Immutable once
    completed or failed (BR-SUP-004's "cannot be silently ignored" depends on every
    check, successful or failed, being retained forever)."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class RegistryStatus(StrEnum):
    """Normalized `supplier.registry_status` per docs/03-domain/policy-engine.md."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class AddressFlag(StrEnum):
    """Normalized `supplier.address_flag` per docs/03-domain/policy-engine.md — a
    heuristic signal, never a BLOCK-tier rule on its own (supplier-compliance.md §4)."""

    CONSISTENT = "consistent"
    FLAGGED = "flagged"
    UNKNOWN = "unknown"
