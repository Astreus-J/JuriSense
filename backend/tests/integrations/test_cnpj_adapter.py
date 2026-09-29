"""STORY-2.5 / ADR-017: `CnpjRegistryAdapter` unit tests, HTTP layer mocked via
`httpx.MockTransport` — the real BrasilAPI call was verified live once (see ADR-017), the
committed suite never touches the network.
"""

import httpx
import pytest

from app.integrations.infrastructure import cnpj_adapter
from app.integrations.infrastructure.cnpj_adapter import CnpjRegistryAdapter


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    monkeypatch.setattr(
        cnpj_adapter,
        "_build_http_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


async def test_fetch_returns_ok_on_200(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/00000000000191")
        return httpx.Response(200, json={"razao_social": "BANCO DO BRASIL SA"})

    _patch_transport(monkeypatch, handler)

    result = await CnpjRegistryAdapter().fetch("00.000.000/0001-91")

    assert result.source == "cnpj_registry"
    assert result.status == "ok"
    assert result.data["razao_social"] == "BANCO DO BRASIL SA"


async def test_fetch_treats_404_as_ok_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transport(monkeypatch, lambda request: httpx.Response(404))

    result = await CnpjRegistryAdapter().fetch("99999999000199")

    assert result.status == "ok"
    assert result.data == {"not_found": True}


async def test_fetch_reports_unavailable_after_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectTimeout("simulated", request=request)

    _patch_transport(monkeypatch, handler)

    result = await CnpjRegistryAdapter(max_retries=2).fetch("00000000000191")

    assert result.status == "unavailable"
    assert calls["count"] == 3  # initial attempt + 2 retries


async def test_fetch_reports_unavailable_on_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_transport(monkeypatch, lambda request: httpx.Response(500))

    result = await CnpjRegistryAdapter(max_retries=0).fetch("00000000000191")

    assert result.status == "unavailable"
