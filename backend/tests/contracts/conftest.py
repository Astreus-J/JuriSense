"""Shared helpers for Contracts & Documents / AI Services tests: RBAC bootstrapping, a
Supplier to attach contracts to, and mocking the AI Gateway's HTTP layer end to end
(hermetic -- no real OpenRouter call; see the EPIC-3 brief's "test suite must not make
live calls" instruction, same discipline as `tests/suppliers/conftest.py`).
"""

import io
import json
from collections.abc import Callable

import httpx
import pypdf
import pytest
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.ai_services.application import extraction_service
from app.ai_services.infrastructure import openrouter_gateway

# Re-exported so contracts tests don't need to know Suppliers' test layout.
from tests.suppliers.conftest import register_org_and_login  # noqa: F401


def pdf_bytes_with_text(text: str = "Contract Agreement Liability Clause") -> bytes:
    """A minimal single-page PDF with genuinely extractable text, built via pypdf's
    low-level object API (no PDF-authoring library like reportlab is a project
    dependency). Every test that exercises the real extraction pipeline needs this, not
    `writer.add_blank_page()` alone: a page with no content stream at all yields empty
    `extract_text()`, which `extraction_service.run_contract_extraction` now correctly
    rejects as `document.processing_failed` (QA review, 2026-09-29) -- a blank PDF is
    unparseable input for these tests' purposes, not valid "successful extraction" test
    data.
    """
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=200, height=200)

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)

    resources = DictionaryObject()
    font_dict = DictionaryObject()
    font_dict[NameObject("/F1")] = font_ref
    resources[NameObject("/Font")] = font_dict
    page[NameObject("/Resources")] = resources

    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(content)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


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

def _envelope_with_min_confidence(confidence: float) -> dict:
    """QA review (2026-09-29): MED-3 -- no test previously pinned the BR-CON-003
    threshold boundary (`contract_extraction_confidence_threshold`, 0.82) exactly, so a
    future `>=` -> `>` regression could ship silently. Builds a single-field envelope at
    exactly the given confidence."""
    return {
        "fields": {
            "contract_type": {
                "value": "saas_subscription",
                "confidence": confidence,
                "provenance": {
                    "document_id": "x",
                    "page": 1,
                    "text_span": {"start": 0, "end": 10},
                },
            },
        },
        "clauses": [],
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

    def apply(
        *,
        payload: dict = HIGH_CONFIDENCE_ENVELOPE,
        status_code: int = 200,
        captured_requests: list[dict] | None = None,
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if captured_requests is not None:
                # #113: lets a test inspect the ACTUAL outgoing request body (the real
                # messages array build_messages produced), not just the mocked response --
                # needed to prove injected document text never escapes into the system
                # prompt or the request's control structure.
                captured_requests.append(json.loads(request.content))
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
