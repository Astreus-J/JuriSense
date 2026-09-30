"""AI Gateway abstraction (`ADR-005`) -- the single interface `Contracts & Documents`
dispatches extraction work through. `docs/04-architecture/components.md` rule 4/5: `AI
Services` returns a validated DTO into its own schema; it never writes to another
context's tables and never calls anything that creates a `ComplianceReview`,
`RuleEvaluation`, or `Decision` (`AI-004`). Concrete adapters (the OpenRouter-backed
implementation today; real OpenAI/Anthropic adapters later, per the ADR-005 addendum)
live in `app/ai_services/infrastructure/`; callers reach this port only through
`app/ai_services/application/extraction_service.py`, never by importing
`app.ai_services.infrastructure` directly (enforced by
`tests/ai_services/test_boundary_rules.py` and `tests/contracts/test_boundary_rules.py`,
mirroring the existing `SupplierVerificationPort` pattern).
"""

from typing import Protocol

from app.ai_services.domain.schema import ExtractionEnvelope


class AIGatewayPort(Protocol):
    """`extract()` per `ADR-005` ("a single internal interface... with pluggable
    provider adapters... and automatic fallback to a secondary provider on
    error/timeout"). `classify()`/`summarize()` are named in the ADR but have no
    consumer yet in this epic -- not implemented here to avoid building unused surface;
    add them when a real caller exists."""

    async def extract_contract(
        self,
        *,
        pages: list[str],
        document_id: str,
        contract_version_id: str,
        pagination_mode: str,
    ) -> ExtractionEnvelope: ...
