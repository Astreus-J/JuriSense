class AIServiceError(Exception):
    """Domain error for the AI Services bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentParsingError(AIServiceError):
    """A file could not be parsed at all (corrupt PDF, non-decodable TXT, ...) --
    maps to `document.processing_failed`
    (`docs/05-ai/document-intelligence.md` "Failure handling"). Raised by
    `app.ai_services.infrastructure.text_extraction`, defined here (domain layer) rather
    than there so callers outside `AI Services` (`Contracts & Documents`) can catch it
    without importing `app.ai_services.infrastructure` directly (boundary rule, same
    reasoning as every other cross-context error type in this codebase)."""


class ExtractionSchemaError(AIServiceError):
    """A provider's raw JSON response did not validate against
    `app.ai_services.domain.schema.ExtractionEnvelope` (AI-002, ADR-005: "rejects and
    retries a response that doesn't validate"). Carries the raw validation detail for
    logging/observability, never persisted as if it were a trusted extraction."""

    def __init__(self, *, provider: str, model: str, detail: str) -> None:
        super().__init__(f"Extraction response from {provider}/{model} failed schema validation")
        self.provider = provider
        self.model = model
        self.detail = detail


class ExtractionProviderError(AIServiceError):
    """One provider/model call failed (HTTP error, timeout, non-2xx, malformed JSON
    body) -- distinct from a schema-validation failure so the fallback logic (AI-003)
    can log which failure mode triggered the fallback."""

    def __init__(self, *, provider: str, model: str, detail: str) -> None:
        super().__init__(f"Extraction call to {provider}/{model} failed: {detail}")
        self.provider = provider
        self.model = model
        self.detail = detail


class AllProvidersExhaustedError(AIServiceError):
    """AI-003's fallback chain (primary -> fallback model) was exhausted without a
    valid, schema-conforming response. Note (ADR-005 addendum): with the interim
    OpenRouter setup, an account-wide daily-quota 429 hits every model on the same
    account identically, so this error does not distinguish "both models are broken"
    from "the account's daily quota is exhausted" -- both surface here the same way,
    and the caller (`Contracts & Documents`) treats this as `document.processing_failed`
    either way."""

    def __init__(self, *, attempts: list[str]) -> None:
        super().__init__(
            "All AI Gateway providers/models were exhausted without a valid extraction: "
            + "; ".join(attempts)
        )
        self.attempts = attempts
