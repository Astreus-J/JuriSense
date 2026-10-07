"""`SupplierEvidenceDTO` -- the plain, read-only DTO `Suppliers` hands `Policy &
Compliance` across the `SupplierEvidencePort` boundary (docs/04-architecture/components.md
rule 3: "return plain DTOs, never SQLAlchemy model instances"). A frozen dataclass, not a
Pydantic model, matching the low-ceremony style of a pure cross-context data carrier that
never gets exposed directly over HTTP (unlike the API-layer `SupplierProfileResponse`,
which is a `BaseModel` because it *is* serialized as an HTTP response body)."""

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupplierEvidenceDTO:
    """The normalized `SupplierProfile` fields the Policy Engine's evaluation context
    consumes (`supplier.*` in `app.policies.domain.context_schema`) -- deliberately a
    strict subset of `SupplierProfile`'s columns: `responsible_parties`/
    `corporate_structure`/`address`/`sanctions_detail` are evidentiary detail a human
    reviewer reads, never a rule's `when` condition (see `context_schema.py`'s
    docstring)."""

    registry_status: str
    sanctions_hit: bool
    activity_mismatch: bool
    address_flag: str
    cnae_code: str | None


@dataclass(frozen=True)
class SupplierIdentityEvidenceDTO:
    """FEATURE-7.3: the Decision Passport's "supplier" field -- `Supplier.legal_name`/
    `tax_id` identify the counterparty itself, not a point-in-time check result, so unlike
    `SupplierEvidenceDTO` this is read live from `Supplier` rather than from the
    `SupplierProfile` current as of the review (`docs/03-domain/evidence.md`'s "Supplier"
    row: "`Supplier.id`, `legal_name`, `tax_id`, plus the SupplierProfile/SupplierCheck
    current as of the review")."""

    supplier_id: uuid.UUID
    legal_name: str
    tax_id: str


@dataclass(frozen=True)
class SupplierCheckEvidenceDTO:
    """One immutable SupplierCheck as `Evidence & Audit` needs it: which external sources it
    consulted (names only) and its raw results, which the caller commits to with a hash and
    never stores in the clear."""

    supplier_check_id: uuid.UUID
    supplier_id: uuid.UUID
    sources_consulted: tuple[str, ...]
    raw_results: dict[str, Any]
