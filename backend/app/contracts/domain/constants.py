"""Contracts & Documents vocabulary -- see docs/03-domain/domain-model.md ("Document",
"Contract", "ContractVersion", "Clause") and docs/03-domain/business-rules.md (BR-CON-*)."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Lifecycle per domain-model.md: uploaded -> processed -> (archived), with a
    processing_failed branch (docs/05-ai/document-intelligence.md "Failure handling")."""

    UPLOADED = "uploaded"
    PROCESSED = "processed"
    PROCESSING_FAILED = "processing_failed"
    ARCHIVED = "archived"


class ContractStatus(StrEnum):
    """Commercial/legal lifecycle per domain-model.md -- independent of any one
    ContractVersion's extraction state (contract-compliance.md)."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    RENEWED = "renewed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class ContractVersionStatus(StrEnum):
    """Per domain-model.md: extracted -> analyzed -> (superseded by next version).
    `needs_confirmation` is the BR-CON-003 gate; `extraction_failed` covers the AI
    Gateway/parsing failure path (document-intelligence.md "Failure handling") -- neither
    is in the domain-model.md diagram verbatim because that diagram describes the happy
    path, but both are necessary, real states this implementation must represent.
    "Superseded" is deliberately not a status this enum tracks: a prior version's row is
    immutable (never edited in place, BR-CON-002), so which version is "current" is
    derived from `version_number` ordering within a `Contract`, never by mutating an
    older version's own status after the fact."""

    EXTRACTED = "extracted"
    NEEDS_CONFIRMATION = "needs_confirmation"
    ANALYZED = "analyzed"
    EXTRACTION_FAILED = "extraction_failed"


# CON-004/BR-CON-004: the clause categories contract-compliance.md names explicitly as
# policy-rule inputs. Not an exhaustive/closed enum at the persistence layer (the AI
# Gateway may identify a clause type not listed here, e.g. an unusual bespoke clause --
# `Clause.clause_type` stays a free-form string so a legitimate extraction is never
# rejected for using a category this list didn't anticipate), but this is the reviewable
# vocabulary the product currently builds policy rules against.
KNOWN_CLAUSE_TYPES = frozenset(
    {
        "liability",
        "termination",
        "confidentiality",
        "dpa",
        "ip",
        "penalties",
        "jurisdiction",
        "indemnification",
        "warranty",
        "force_majeure",
        "assignment",
        "sla",
    }
)
