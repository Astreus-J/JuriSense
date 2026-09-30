"""`SupplierEvidenceDTO` -- the plain, read-only DTO `Suppliers` hands `Policy &
Compliance` across the `SupplierEvidencePort` boundary (docs/04-architecture/components.md
rule 3: "return plain DTOs, never SQLAlchemy model instances"). A frozen dataclass, not a
Pydantic model, matching the low-ceremony style of a pure cross-context data carrier that
never gets exposed directly over HTTP (unlike the API-layer `SupplierProfileResponse`,
which is a `BaseModel` because it *is* serialized as an HTTP response body)."""

from dataclasses import dataclass


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
