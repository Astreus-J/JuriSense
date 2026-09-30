"""`ContractEvidenceDTO` -- the plain, read-only DTO `Contracts & Documents` hands
`Policy & Compliance` across the `ContractEvidencePort` boundary
(docs/04-architecture/components.md rule 3). Mirrors
`app.suppliers.domain.evidence.SupplierEvidenceDTO`'s role and rationale."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContractEvidenceDTO:
    """The normalized `contract.*` fields the Policy Engine's evaluation context consumes
    (`app.policies.domain.context_schema.CONTRACT_CONTEXT_PATHS`) -- each leaf is the bare
    `.value` already stripped of `ExtractedValue`'s `confidence`/`provenance` wrapper
    (BR-CMP-001: rules evaluate normalized evidence, never raw AI output). A field the
    source document never mentioned is `None` here; the context builder omits it from the
    flat evaluation context entirely rather than passing the `None` through (see
    `app.policies.domain.context_schema`'s docstring on why "omitted" and "explicit null"
    are not interchangeable for the CEL compiler)."""

    contract_type: str | None
    value_amount: float | None
    value_currency: str | None
    duration_start_date: str | None
    duration_end_date: str | None
    duration_auto_renewal: bool | None
    termination_notice_period_days: int | None
    termination_for_convenience: bool | None
    liability_type: str | None
    liability_cap: float | None
    processes_personal_data: bool | None
    dpa_present: bool | None
    jurisdiction: str | None


def _leaf_value(fields: dict[str, Any], *path: str) -> Any:
    """Walks a `ContractVersion.extracted_data["fields"]` dict (the JSON-persisted form
    of `app.ai_services.domain.schema.ContractFields`) and returns one leaf's bare
    `.value`, or `None` if any segment along `path` is absent or the leaf itself is
    `None` (a term the extraction genuinely never found)."""
    node: Any = fields
    for segment in path:
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    if not isinstance(node, dict):
        return None
    return node.get("value")


def contract_fields_to_evidence_dto(fields: dict[str, Any]) -> ContractEvidenceDTO:
    """Pure transform: `ContractVersion.extracted_data["fields"]` (a plain dict, the
    JSON-persisted `ContractFields`) -> `ContractEvidenceDTO`. Separated from
    `evidence_service.get_normalized_terms` so it can be unit-tested without a database."""
    return ContractEvidenceDTO(
        contract_type=_leaf_value(fields, "contract_type"),
        value_amount=_leaf_value(fields, "value", "amount"),
        value_currency=_leaf_value(fields, "value", "currency"),
        duration_start_date=_leaf_value(fields, "duration", "start_date"),
        duration_end_date=_leaf_value(fields, "duration", "end_date"),
        duration_auto_renewal=_leaf_value(fields, "duration", "auto_renewal"),
        termination_notice_period_days=_leaf_value(fields, "termination", "notice_period_days"),
        termination_for_convenience=_leaf_value(
            fields, "termination", "termination_for_convenience"
        ),
        liability_type=_leaf_value(fields, "liability", "type"),
        liability_cap=_leaf_value(fields, "liability", "cap"),
        processes_personal_data=_leaf_value(fields, "privacy", "processes_personal_data"),
        dpa_present=_leaf_value(fields, "privacy", "dpa_present"),
        jurisdiction=_leaf_value(fields, "jurisdiction"),
    )
