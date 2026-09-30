"""AI-001/AI-002/AI-003: the OpenRouter-backed AI Gateway adapter, entirely hermetic
(mocked HTTP transport, no real network call -- same discipline as
`tests/suppliers/conftest.py`'s `mock_cnpj_registry`). Exercises the fallback chain
(primary model error/invalid-schema -> fallback model) and the "all providers exhausted"
terminal failure.
"""

import json

import httpx
import pytest

from app.ai_services.domain.errors import AllProvidersExhaustedError
from app.ai_services.infrastructure import openrouter_gateway

_VALID_MODEL_OUTPUT = {
    "fields": {
        "contract_type": {
            "value": "nda",
            "confidence": 0.95,
            "provenance": {
                "document_id": "SHOULD-BE-OVERWRITTEN",
                "page": 1,
                "text_span": {"start": 0, "end": 10},
            },
        }
    },
    "clauses": [
        {
            "clause_type": "confidentiality",
            "page": 1,
            "text_span": {"start": 0, "end": 100},
            "confidence": 0.9,
        }
    ],
}


def _chat_completion_response(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


def _mock_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    def build_client(*, base_url: str, api_key: str, timeout_seconds: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(openrouter_gateway, "_build_http_client", build_client)


def _gateway() -> openrouter_gateway.OpenRouterAIGateway:
    return openrouter_gateway.OpenRouterAIGateway(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        primary_model="primary/model:free",
        fallback_model="fallback/model:free",
        timeout_seconds=5.0,
    )


async def test_successful_primary_model_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "primary/model:free"
        return httpx.Response(200, json=_chat_completion_response(_VALID_MODEL_OUTPUT))

    _mock_client(monkeypatch, handler)
    envelope = await _gateway().extract_contract(
        pages=["Page one text."],
        document_id="doc-123",
        contract_version_id="version-123",
        pagination_mode="native",
    )

    assert envelope.model.model_name == "primary/model:free"
    assert envelope.fields.contract_type.value == "nda"
    # Provenance document_id is forcibly stamped to the real document_id, never trusted
    # verbatim from the model's own output.
    assert envelope.fields.contract_type.provenance.document_id == "doc-123"
    assert envelope.clauses[0].clause_type == "confidentiality"


async def test_falls_back_to_secondary_model_on_primary_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body["model"])
        if body["model"] == "primary/model:free":
            return httpx.Response(500, text="internal error")
        return httpx.Response(200, json=_chat_completion_response(_VALID_MODEL_OUTPUT))

    _mock_client(monkeypatch, handler)
    envelope = await _gateway().extract_contract(
        pages=["Page one text."],
        document_id="doc-123",
        contract_version_id="version-123",
        pagination_mode="native",
    )
    assert envelope.model.model_name == "fallback/model:free"
    assert "primary/model:free" in calls
    assert "fallback/model:free" in calls


async def test_falls_back_to_secondary_model_on_schema_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["model"] == "primary/model:free":
            # Malformed: confidence out of [0, 1] range -- fails schema validation.
            bad_output = {
                "fields": {
                    "contract_type": {
                        "value": "nda",
                        "confidence": 5.0,
                        "provenance": {
                            "document_id": "x",
                            "page": 1,
                            "text_span": {"start": 0, "end": 1},
                        },
                    }
                },
                "clauses": [],
            }
            return httpx.Response(200, json=_chat_completion_response(bad_output))
        return httpx.Response(200, json=_chat_completion_response(_VALID_MODEL_OUTPUT))

    _mock_client(monkeypatch, handler)
    envelope = await _gateway().extract_contract(
        pages=["Page one text."],
        document_id="doc-123",
        contract_version_id="version-123",
        pagination_mode="native",
    )
    assert envelope.model.model_name == "fallback/model:free"


async def test_all_providers_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    _mock_client(monkeypatch, handler)
    with pytest.raises(AllProvidersExhaustedError):
        await _gateway().extract_contract(
            pages=["Page one text."],
            document_id="doc-123",
            contract_version_id="version-123",
            pagination_mode="native",
        )
