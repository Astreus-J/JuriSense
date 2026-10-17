"""Gemini-backed `AIGatewayPort` adapter (2026-10-16 addendum to `ADR-005`).

Google's Generative Language API is not OpenAI-compatible (different endpoint shape,
auth via a `key` query param, `contents`/`generationConfig` instead of
`messages`/`response_format`), so this is a genuinely separate adapter rather than a
config-only swap on `OpenRouterAIGateway` -- unlike pointing the OpenRouter adapter at a
different model, which ADR-005's own docstring already covers. Reuses
`prompt_builder.build_messages()` for the actual prompt content (system/user text is
provider-agnostic); only the request/response envelope differs.

Mirrors `openrouter_gateway.py`'s fallback behavior: `[primary_model, fallback_model]`,
one same-model retry each, `response_format`'s `strict: False` precedent -- this adapter
likewise asks for `responseMimeType: "application/json"` only (no `responseSchema`:
Pydantic's `model_json_schema()` output uses `$ref`/`$defs`/`anyOf`-null that Gemini's
OpenAPI-3.0-subset schema format does not accept without a nontrivial rewrite) and relies
on the same client-side `ModelExtractionOutput` validation OpenRouter's path already does
as the actual correctness gate -- consistent with how the existing adapter already treats
the provider's own schema enforcement as a hint, not the source of truth.
"""

import asyncio
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
from app.ai_services.infrastructure.prompt_builder import PROMPT_VERSION, build_messages

logger = logging.getLogger("jurisense.ai_services.gateway")

_PROVIDER_NAME = "gemini"
_RETRIES_PER_MODEL = 1

# QA review (2026-10-16): without this, Gemini received no machine-readable schema at
# all -- unlike the OpenRouter path, which passes ModelExtractionOutput's JSON Schema
# via `response_format` (prompt_builder.build_response_format()). The shared prose
# system prompt alone was empirically confirmed insufficient: a real response put
# `contract_type`/`parties`/`duration` etc. at the document's top level instead of
# nested under `fields`, and gave `clauses[]` entries a `provenance` wrapper + `title`
# field that don't exist in `ClauseExtraction`. Appending the exact same schema
# OpenRouter already sends (as inline prompt text rather than a `responseSchema` API
# parameter -- Gemini's `responseSchema` is a distinct OpenAPI-3.0 subset that doesn't
# accept Pydantic's `$ref`/`$defs`/nullable-`anyOf` output without a nontrivial rewrite)
# fixed this in testing without touching the shared prose instructions other callers
# also rely on.
_SCHEMA_TEXT = json.dumps(ModelExtractionOutput.model_json_schema())


def _build_http_client(*, base_url: str, timeout_seconds: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout_seconds, connect=10.0),
        headers={"Content-Type": "application/json"},
    )


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


class GeminiAIGateway:
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
        system_text = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_text = next((m["content"] for m in messages if m["role"] == "user"), "")
        user_text = (
            f"{user_text}\n\n"
            "Required output JSON Schema -- your response MUST be a single JSON object "
            "matching this schema exactly (top-level keys are exactly `fields` and "
            f"`clauses`, nothing else):\n\n{_SCHEMA_TEXT}"
        )

        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                # This is deterministic structured extraction, not open-ended
                # reasoning -- chain-of-thought "thinking" tokens (confirmed present,
                # `thoughtsTokenCount`, in a real response during testing 2026-10-16)
                # only add latency and cost here. Not every model on this fallback
                # list supports `thinkingConfig` -- a model that rejects the field
                # falls through to ExtractionProviderError and the next model in the
                # chain, same as any other provider-side rejection.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        async with _build_http_client(
            base_url=self._base_url, timeout_seconds=self._timeout_seconds
        ) as client:
            try:
                # See module docstring on openrouter_gateway.py's identical guard (QA
                # review 2026-10-16): httpx's own configured read timeout was
                # empirically confirmed not to bound a stalled response body reliably --
                # an explicit outer wait_for is a second, independent bound.
                response = await asyncio.wait_for(
                    client.post(
                        f"/models/{model}:generateContent",
                        params={"key": self._api_key},
                        json=payload,
                    ),
                    timeout=self._timeout_seconds + 10,
                )
            except TimeoutError as exc:
                raise ExtractionProviderError(
                    provider=_PROVIDER_NAME,
                    model=model,
                    detail=f"Stalled response (no body after {self._timeout_seconds + 10:.0f}s)",
                ) from exc
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
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
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
