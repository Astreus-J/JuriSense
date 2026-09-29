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


# Security/QA review (2026-09-29) found `update_supplier_status` accepted any status as a
# target from any current status -- domain-model.md's documented lifecycle diagram
# (`prospect -> under_review -> approved|blocked -> inactive`) was never actually enforced
# as a state machine, only BR-SUP-003's extra gate on the `approved` target was. This table
# is the enforcement: a `prospect` can be rejected outright (`blocked`) without a full
# review, `approved`/`blocked` can both retire to `inactive`, and `approved` can be revoked
# back to `blocked` (e.g. a re-check surfaces a new adverse finding) -- but `inactive` is
# terminal (retired suppliers are superseded by a new record, never reopened, matching this
# system's append-only/immutable-history philosophy) and no transition ever skips backward
# into `under_review` or `prospect`.
ALLOWED_STATUS_TRANSITIONS: dict[SupplierStatus, frozenset[SupplierStatus]] = {
    SupplierStatus.PROSPECT: frozenset({SupplierStatus.UNDER_REVIEW, SupplierStatus.BLOCKED}),
    SupplierStatus.UNDER_REVIEW: frozenset({SupplierStatus.APPROVED, SupplierStatus.BLOCKED}),
    SupplierStatus.APPROVED: frozenset({SupplierStatus.BLOCKED, SupplierStatus.INACTIVE}),
    SupplierStatus.BLOCKED: frozenset({SupplierStatus.INACTIVE}),
    SupplierStatus.INACTIVE: frozenset(),
}


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
