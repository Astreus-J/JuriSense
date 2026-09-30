"""Shared helpers for Contracts & Documents / AI Services tests: RBAC bootstrapping, a
Supplier to attach contracts to, and mocking the AI Gateway's HTTP layer end to end
(hermetic -- no real OpenRouter call; see the EPIC-3 brief's "test suite must not make
live calls" instruction, same discipline as `tests/suppliers/conftest.py`).
"""

import json
from collections.abc import Callable

import httpx
import pytest

from app.ai_services.application import extraction_service
from app.ai_services.infrastructure import openrouter_gateway

# Re-exported so contracts tests don't need to know Suppliers' test layout.
from tests.suppliers.conftest import register_org_and_login  # noqa: F401

HIGH_CONFIDENCE_ENVELOPE = {
    "fields": {
        "contract_type": {
            "value": "saas_subscription",
            "confidence": 0.95,
            "provenance": {"document_id": "x", "page": 1, "text_span": {"start": 0, "end": 10}},
        },
        "liability": {
            "type": {
                "value": "capped",
                "confidence": 0.93,
                "provenance": {"document_id": "x", "page": 2, "text_span": {"start": 0, "end": 10}},
            }
        },
        "privacy": {
            "processes_personal_data": {
                "value": True,
                "confidence": 0.9,
                "provenance": {"document_id": "x", "page": 3, "text_span": {"start": 0, "end": 10}},
            },
            "dpa_present": {
                "value": True,
                "confidence": 0.92,
                "provenance": {
                    "document_id": "x",
                    "page": 3,
                    "text_span": {"start": 10, "end": 20},
                },
            },
        },
    },
    "clauses": [
        {
            "clause_type": "liability",
            "page": 2,
            "text_span": {"start": 0, "end": 10},
            "confidence": 0.93,
            "text_excerpt": "Liability is capped at contract value.",
        }
    ],
}

LOW_CONFIDENCE_ENVELOPE = {
    "fields": {
        "contract_type": {
            "value": "nda",
            "confidence": 0.95,
            "provenance": {"document_id": "x", "page": 1, "text_span": {"start": 0, "end": 10}},
        },
        "liability": {
            "type": {
                "value": "unlimited",
                "confidence": 0.4,  # below the default 0.82 threshold
                "provenance": {"document_id": "x", "page": 2, "text_span": {"start": 0, "end": 10}},
            }
        },
    },
    "clauses": [],
}


@pytest.fixture
def mock_openrouter(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Returns `apply(payload=..., status_code=200)` to control what the AI Gateway's
    HTTP layer sees, without any real OpenRouter call. Also swaps
    `extraction_service.get_ai_gateway` so tests never depend on a real
    `OPENROUTER_API_KEY` being configured."""

    def apply(*, payload: dict = HIGH_CONFIDENCE_ENVELOPE, status_code: int = 200) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if status_code != 200:
                return httpx.Response(status_code, text="error")
            return httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(payload)}}]}
            )

        def build_client(
            *, base_url: str, api_key: str, timeout_seconds: float
        ) -> httpx.AsyncClient:
            return httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(handler))

        monkeypatch.setattr(openrouter_gateway, "_build_http_client", build_client)
        monkeypatch.setattr(
            extraction_service,
            "get_ai_gateway",
            lambda: openrouter_gateway.OpenRouterAIGateway(
                base_url="https://openrouter.ai/api/v1",
                api_key="test-key",
                primary_model="primary/model:free",
                fallback_model="fallback/model:free",
                timeout_seconds=5.0,
            ),
        )

    return apply


async def create_supplier(client: httpx.AsyncClient, headers: dict, *, tax_id: str) -> dict:
    response = await client.post(
        "/api/suppliers",
        json={"legal_name": "Test Supplier Ltda.", "tax_id": tax_id, "jurisdiction": "BR"},
        headers=headers,
    )
    return response.json()
