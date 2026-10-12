"""AI-002: the structured-extraction schema (`docs/05-ai/structured-extraction.md`)
validates a well-formed response and rejects a malformed one -- this is the backbone of
"the AI Gateway rejects and retries a response that doesn't validate" (ADR-005).
"""

import pytest
from pydantic import ValidationError

from app.ai_services.domain.schema import ModelExtractionOutput

_PROVENANCE = {
    "document_id": "11111111-1111-1111-1111-111111111111",
    "page": 1,
    "text_span": {"start": 0, "end": 10},
}


def _extracted_value(value: object, confidence: float = 0.9) -> dict:
    return {"value": value, "confidence": confidence, "provenance": _PROVENANCE}


def test_worked_example_from_docs_validates() -> None:
    """A close transcription of structured-extraction.md's own worked example."""
    payload = {
        "fields": {
            "contract_type": _extracted_value("saas_subscription", 0.95),
            "liability": {
                "type": _extracted_value("unlimited", 0.91),
                "cap": _extracted_value(None, 0.91),
            },
            "privacy": {
                "processes_personal_data": _extracted_value(True, 0.94),
                "dpa_present": _extracted_value(False, 0.89),
            },
            "obligations": [_extracted_value("Maintain 99.9% uptime SLA.", 0.87)],
        },
        "clauses": [
            {
                "clause_type": "liability",
                "page": 5,
                "text_span": {"start": 2900, "end": 3050},
                "confidence": 0.91,
                "text_excerpt": "Supplier's liability shall be unlimited...",
            }
        ],
    }
    output = ModelExtractionOutput.model_validate(payload)
    assert output.fields.liability.type.value == "unlimited"
    assert output.clauses[0].clause_type == "liability"


def test_confidence_out_of_range_rejected() -> None:
    payload = {"fields": {"contract_type": _extracted_value("nda", confidence=1.5)}}
    with pytest.raises(ValidationError):
        ModelExtractionOutput.model_validate(payload)


def test_clause_missing_page_rejected() -> None:
    payload = {
        "fields": {},
        "clauses": [
            {"clause_type": "dpa", "text_span": {"start": 0, "end": 10}, "confidence": 0.8}
        ],
    }
    with pytest.raises(ValidationError):
        ModelExtractionOutput.model_validate(payload)


def test_extra_unexpected_key_rejected() -> None:
    """`extra="forbid"` on every schema model -- a provider hallucinating an unexpected
    top-level key must fail validation, not be silently ignored."""
    payload = {"fields": {}, "clauses": [], "not_a_real_field": True}
    with pytest.raises(ValidationError):
        ModelExtractionOutput.model_validate(payload)
