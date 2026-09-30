"""Application-layer seam `Contracts & Documents` calls to run extraction (CON-003,
AI-001). Mirrors `app.integrations.application.supplier_verification_service`: other
bounded contexts call a plain function here, never `app.ai_services.infrastructure`
directly (enforced by `tests/ai_services/test_boundary_rules.py` and
`tests/contracts/test_boundary_rules.py`).
"""

from app.ai_services.domain.errors import DocumentParsingError
from app.ai_services.domain.ports import AIGatewayPort
from app.ai_services.domain.schema import ExtractionEnvelope
from app.ai_services.infrastructure.openrouter_gateway import OpenRouterAIGateway
from app.ai_services.infrastructure.prompt_builder import truncate_pages
from app.ai_services.infrastructure.text_extraction import ExtractedDocument, extract_text
from app.core.config import get_settings


def get_ai_gateway() -> AIGatewayPort:
    """Builds the current `AIGatewayPort` implementation from `Settings` -- swapping to a
    real OpenAI/Anthropic key later only changes these values
    (`docs/adr/ADR-005-addendum-interim-ai-provider.md`), never this call site."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured -- the AI Gateway cannot run extraction"
        )
    return OpenRouterAIGateway(
        base_url=settings.ai_gateway_base_url,
        api_key=settings.openrouter_api_key,
        primary_model=settings.ai_extraction_primary_model,
        fallback_model=settings.ai_extraction_fallback_model,
        timeout_seconds=settings.ai_extraction_timeout_seconds,
    )


def extract_document_pages(data: bytes, mime_type: str) -> ExtractedDocument:
    """Thin re-export of the infrastructure-layer text extractor so callers in
    `Contracts & Documents` only ever import from `app.ai_services.application`, never
    `app.ai_services.infrastructure` (same boundary rule as the gateway itself)."""
    return extract_text(data, mime_type)


async def run_contract_extraction(
    *,
    document_id: str,
    contract_version_id: str,
    document_bytes: bytes,
    mime_type: str,
) -> ExtractionEnvelope:
    """Runs the full extraction pipeline for one `ContractVersion` (CON-003): text
    extraction -> AI Gateway call with fallback (AI-003) -> schema-validated result
    (AI-002). Raises `app.ai_services.infrastructure.text_extraction.DocumentParsingError`
    on an unparseable file, or `app.ai_services.domain.errors.AllProvidersExhaustedError`
    if every provider/model attempt failed -- both map to `document.processing_failed` in
    the caller (`app.contracts.application.extraction_orchestration`).
    """
    settings = get_settings()
    extracted = extract_document_pages(document_bytes, mime_type)
    # QA review (2026-09-29): `text_extraction.py`'s own module docstring already
    # documented this as the intended behavior ("an entirely-empty document ... a
    # parsing failure"), but nothing actually implemented it -- a scanned/image-only PDF
    # (no OCR yet, a documented TBD) silently proceeded to the AI Gateway with blank
    # page content instead of failing fast. `not text.strip()` treats whitespace-only
    # pages the same as truly empty ones.
    if all(not page.strip() for page in extracted.pages):
        raise DocumentParsingError(
            "Document yielded no extractable text (possibly a scanned/image-only file "
            "-- OCR is not yet supported, see docs/05-ai/document-intelligence.md)"
        )
    pages = truncate_pages(extracted.pages, max_chars=settings.ai_extraction_max_input_chars)

    gateway = get_ai_gateway()
    return await gateway.extract_contract(
        pages=pages,
        document_id=document_id,
        contract_version_id=contract_version_id,
        pagination_mode=extracted.pagination_mode,
    )
