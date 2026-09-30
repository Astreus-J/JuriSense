"""OpenRouter-backed `AIGatewayPort` adapter (`docs/adr/ADR-005-addendum-interim-ai-provider.md`).

OpenRouter exposes an OpenAI-compatible chat completions API
(`{base_url}/chat/completions`), so this adapter is written against that interface --
pointing it at real OpenAI/Anthropic later is a pure config change (`Settings.ai_gateway_base_url`
+ model names), never a code change, per ADR-005's original "OpenAI adapter" framing.

Fallback (AI-003): on any provider/HTTP error, timeout, or a response that fails schema
validation after one same-model retry, the adapter tries the next model in
`[primary_model, fallback_model]`. Documented limitation (see the ADR-005 addendum): both
models share the same OpenRouter account, so a 429 from the account-wide free-tier daily
quota (50 requests/day) will hit both identically -- this fallback protects against a
single model's own errors/timeouts/malformed output, not against quota exhaustion.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from app.ai_services.domain.errors import (
    AllProvidersExhaustedError,
    ExtractionProviderError,
    ExtractionSchemaError,
)
from app.ai_services.domain.schema import ExtractionEnvelope, ModelExtractionOutput, ModelInfo
from app.ai_services.infrastructure.prompt_builder import (
    PROMPT_VERSION,
    build_messages,
    build_response_format,
)

logger = logging.getLogger("jurisense.ai_services.gateway")

_PROVIDER_NAME = "openrouter"
_RETRIES_PER_MODEL = 1  # one same-model retry on a schema-validation failure, then fall back


def _build_http_client(*, base_url: str, api_key: str, timeout_seconds: float) -> httpx.AsyncClient:
    """Test seam: monkeypatched in tests to bind to `httpx.MockTransport`, the same
    pattern `app.integrations.infrastructure.cnpj_adapter._build_http_client` uses."""
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout_seconds, connect=10.0),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter-recommended attribution headers; harmless no-ops on a real
            # OpenAI/Anthropic endpoint if this adapter is ever pointed there directly.
            "HTTP-Referer": "https://jurisense.local",
            "X-Title": "JuriSense Gate",
        },
    )


class OpenRouterAIGateway:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        primary_model: str,
        fallback_model: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._models = [primary_model, fallback_model]
        self._timeout_seconds = timeout_seconds

    async def _call_model(self, *, model: str, messages: list[dict[str, str]]) -> dict:
        async with _build_http_client(
            base_url=self._base_url, api_key=self._api_key, timeout_seconds=self._timeout_seconds
        ) as client:
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "response_format": build_response_format(),
                        "temperature": 0.0,
                    },
                )
            except httpx.HTTPError as exc:
                raise ExtractionProviderError(
                    provider=_PROVIDER_NAME, model=model, detail=f"{type(exc).__name__}: {exc}"
                ) from exc

        if response.status_code != 200:
            raise ExtractionProviderError(
                provider=_PROVIDER_NAME,
                model=model,
                detail=f"HTTP {response.status_code}: {response.text[:500]}",
            )
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise ExtractionProviderError(
                provider=_PROVIDER_NAME, model=model, detail=f"Malformed response body: {exc}"
            ) from exc

    def _validate(self, raw: dict, *, model: str, document_id: str) -> ModelExtractionOutput:
        try:
            parsed = ModelExtractionOutput.model_validate(raw)
        except ValidationError as exc:
            raise ExtractionSchemaError(
                provider=_PROVIDER_NAME, model=model, detail=str(exc)
            ) from exc
        # Defensive: force every provenance.document_id to the known-correct value
        # rather than trusting the model to echo it back verbatim (AI-002) -- removes
        # one entire, avoidable class of schema/consistency failures.
        return _stamp_document_id(parsed, document_id=document_id)

    async def extract_contract(
        self,
        *,
        pages: list[str],
        document_id: str,
        contract_version_id: str,
        pagination_mode: str,
    ) -> ExtractionEnvelope:
        messages = build_messages(document_id=document_id, pages=pages)
        attempts: list[str] = []

        for model in self._models:
            for attempt in range(_RETRIES_PER_MODEL + 1):
                try:
                    raw = await self._call_model(model=model, messages=messages)
                    output = self._validate(raw, model=model, document_id=document_id)
                except (ExtractionProviderError, ExtractionSchemaError) as exc:
                    attempts.append(f"{model} (attempt {attempt + 1}): {exc.message}")
                    logger.warning(
                        "Extraction attempt failed (%s, attempt %d/%d): %s",
                        model,
                        attempt + 1,
                        _RETRIES_PER_MODEL + 1,
                        exc.message,
                    )
                    continue
                return ExtractionEnvelope(
                    contract_version_id=contract_version_id,
                    document_id=document_id,
                    extraction_run_id=str(uuid.uuid4()),
                    model=ModelInfo(
                        provider=_PROVIDER_NAME, model_name=model, prompt_version=PROMPT_VERSION
                    ),
                    extracted_at=datetime.now(UTC).isoformat(),
                    pagination_mode=pagination_mode,
                    fields=output.fields,
                    clauses=output.clauses,
                )

        raise AllProvidersExhaustedError(attempts=attempts)


def _stamp_document_id(output: ModelExtractionOutput, *, document_id: str) -> ModelExtractionOutput:
    data = output.model_dump()

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            if "provenance" in node and isinstance(node["provenance"], dict):
                node["provenance"]["document_id"] = document_id
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)
    return ModelExtractionOutput.model_validate(data)
