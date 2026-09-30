"""Builds the extraction prompt + JSON schema sent to the AI Gateway (`ADR-005`:
"structured output... never freeform text parsing").
"""

import json

from app.ai_services.domain.schema import ModelExtractionOutput

PROMPT_VERSION = "contract-extraction-v1"

_SYSTEM_PROMPT = """You are a contract data extraction engine for a B2B vendor/contract \
compliance platform. You are given the full text of a commercial contract, split into \
pages, and must return ONLY a JSON object matching the provided schema -- no prose, no \
markdown fences.

Rules:
- Every extracted value must be wrapped with its confidence (0..1) and provenance \
(document_id, page, text_span).
- `text_span.start`/`text_span.end` are character offsets INTO THE TEXT OF THE PAGE YOU \
CITE, not the whole document -- each page's text below starts a fresh offset 0.
- Never invent a value that is not actually supported by the text you cite -- if a field \
is not present in the contract, omit it (leave it null/absent) rather than guessing.
- `document_id` in every provenance object must be exactly the document_id given below.
- Identify every distinct clause (liability, termination, confidentiality, dpa, ip, \
penalties, jurisdiction, etc.) in `clauses[]`, each with its own page/text_span/confidence.
- Confidence should reflect your actual certainty: a clearly-stated fact is high \
confidence (>0.9); an inferred or ambiguous one should be scored lower, honestly."""


def build_messages(
    *, document_id: str, pages: list[str]
) -> list[dict[str, str]]:
    page_blocks = "\n\n".join(f"--- PAGE {i + 1} ---\n{text}" for i, text in enumerate(pages))
    user_prompt = (
        f"document_id: {document_id}\n\n"
        f"Contract text ({len(pages)} page(s)):\n\n{page_blocks}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_response_format() -> dict:
    """`response_format: json_schema` per the OpenAI-compatible API surface the ADR-005
    addendum's OpenRouter models were verified to support (`supported_parameters`
    includes `response_format`/`structured_outputs`)."""
    schema = ModelExtractionOutput.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "contract_extraction",
            "schema": schema,
            "strict": False,
        },
    }


def truncate_pages(pages: list[str], *, max_chars: int) -> list[str]:
    """Documented scope decision (see `Settings.ai_extraction_max_input_chars`): a
    simple whole-document character budget, not the structural chunking
    `document-intelligence.md` describes for long contracts. Pages are kept whole up to
    the budget rather than cut mid-page."""
    total = 0
    kept: list[str] = []
    for page in pages:
        if total + len(page) > max_chars and kept:
            break
        kept.append(page)
        total += len(page)
    return kept or pages[:1]


def dumps_for_log(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)[:2000]
