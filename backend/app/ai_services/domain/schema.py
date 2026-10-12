"""Structured-extraction schema (AI-002, `docs/05-ai/structured-extraction.md`).

This is a literal Pydantic transcription of that document's JSON Schema -- the exact
contract `AI Services` produces and `Contracts & Documents` persists into
`ContractVersion.extracted_data`. Every leaf value is wrapped with `confidence` and
`provenance` (never a bare value); array items carry their own wrapper too. The AI
Gateway validates a provider's raw JSON response against this schema before it is
trusted -- an invalid response is rejected/retried, never persisted
(`docs/03-domain/business-rules.md` BR-CON-004, `AI-002`).
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class TextSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class Provenance(BaseModel):
    """Every extracted fact's back-reference to its source document
    (`docs/05-ai/document-intelligence.md` "Text span provenance")."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    page: int = Field(ge=1)
    text_span: TextSpan


class ExtractedValue(BaseModel):
    """The universal leaf wrapper -- `structured-extraction.md`'s `extractedValue`
    (and its `extractedString`/`extractedNumber`/`extractedBoolean`/`extractedDate`
    specializations, which only narrow `value`'s type at the call-site level)."""

    model_config = ConfigDict(extra="forbid")

    value: Any
    confidence: Confidence
    provenance: Provenance


class PartyValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    name: str
    tax_id: str | None = None


class ValueFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: ExtractedValue | None = None
    currency: ExtractedValue | None = None


class DurationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: ExtractedValue | None = None
    end_date: ExtractedValue | None = None
    auto_renewal: ExtractedValue | None = None


class TerminationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice_period_days: ExtractedValue | None = None
    termination_for_convenience: ExtractedValue | None = None
    termination_for_cause_conditions: ExtractedValue | None = None


class LiabilityFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ExtractedValue | None = None
    cap: ExtractedValue | None = None


class PrivacyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processes_personal_data: ExtractedValue | None = None
    dpa_present: ExtractedValue | None = None


class DeadlineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    date: ExtractedValue | None = None


class ContractFields(BaseModel):
    """`fields` object -- see `structured-extraction.md`'s worked example for the exact
    shape. Every leaf is optional at the schema level (a contract may simply not mention
    a given term) but each present leaf must be a fully-formed `ExtractedValue`."""

    model_config = ConfigDict(extra="forbid")

    contract_type: ExtractedValue | None = None
    parties: ExtractedValue | None = None
    value: ValueFields = Field(default_factory=ValueFields)
    duration: DurationFields = Field(default_factory=DurationFields)
    termination: TerminationFields = Field(default_factory=TerminationFields)
    liability: LiabilityFields = Field(default_factory=LiabilityFields)
    privacy: PrivacyFields = Field(default_factory=PrivacyFields)
    obligations: list[ExtractedValue] = Field(default_factory=list)
    subprocessors: list[ExtractedValue] = Field(default_factory=list)
    jurisdiction: ExtractedValue | None = None
    guarantees: list[ExtractedValue] = Field(default_factory=list)
    penalties: list[ExtractedValue] = Field(default_factory=list)
    deadlines: list[DeadlineItem] = Field(default_factory=list)


class ClauseExtraction(BaseModel):
    """One `clauses[]` entry -- the direct source for `Clause` rows
    (`docs/03-domain/domain-model.md`). `page`/`text_span`/`confidence` are required,
    never optional: BR-CON-004 makes a clause without provenance unusable as evidence,
    so the schema itself refuses to represent one."""

    model_config = ConfigDict(extra="forbid")

    clause_type: str
    page: int = Field(ge=1)
    text_span: TextSpan
    confidence: Confidence
    text_excerpt: str | None = None


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model_name: str
    prompt_version: str


class ModelExtractionOutput(BaseModel):
    """The subset of `ExtractionEnvelope` the provider actually has to produce --
    `contract_version_id`/`document_id`/`extraction_run_id`/`model`/`extracted_at`/
    `pagination_mode` are known deterministically by the caller (`extraction_service`),
    which fills them in itself rather than trusting a model to echo them back correctly
    (avoids one whole class of avoidable schema-validation failures)."""

    model_config = ConfigDict(extra="forbid")

    fields: ContractFields = Field(default_factory=ContractFields)
    clauses: list[ClauseExtraction] = Field(default_factory=list)


class ExtractionEnvelope(BaseModel):
    """The full top-level response `extract_contract()` produces and validates
    (`ADR-005`: "structured output only... rejects and retries a response that doesn't
    validate").

    #144 (2026-10-12): this class used to carry its own `all_field_confidences()`,
    walking this Pydantic model tree -- a second, independent implementation of "every
    leaf confidence" alongside `app.contracts.domain.extracted_data.iter_field_leaves`/
    `min_confidence`, which walk the PERSISTED `extracted_data` JSON dict instead (the
    shape `extraction_service` actually stores and the BR-CON-003 confidence gate and
    CON-005 confirmation endpoint actually read). `all_field_confidences` was never
    called by production code -- only by its own unit test -- so it was removed rather
    than consolidated: the JSON-dict walker in `extracted_data.py` is the one real
    implementation of this rule now."""

    model_config = ConfigDict(extra="forbid")

    contract_version_id: str
    document_id: str
    extraction_run_id: str
    model: ModelInfo
    extracted_at: str
    pagination_mode: str = Field(pattern="^(native|synthetic)$")
    fields: ContractFields = Field(default_factory=ContractFields)
    clauses: list[ClauseExtraction] = Field(default_factory=list)
