"""STORY-2.5 / ADR-017: `PortalTransparenciaSanctionsSource` unit tests. The real bulk
CSV/zip download and format (ISO-8859-1, semicolon-delimited, CRLF) were verified live
once by actually downloading CEIS/CNEP/CEPIM extracts on 2026-09-28 (see ADR-017); this
suite mocks the HTTP layer so it never touches the network.
"""

import io
import zipfile

import httpx
import pytest

from app.integrations.domain.constants import SanctionsList
from app.integrations.infrastructure import sanctions_source
from app.integrations.infrastructure.sanctions_source import PortalTransparenciaSanctionsSource

_CEIS_HEADER = (
    '"CADASTRO";"CÓDIGO DA SANÇÃO";"TIPO DE PESSOA";"CPF OU CNPJ DO SANCIONADO";'
    '"NOME DO SANCIONADO";"CATEGORIA DA SANÇÃO"\r\n'
)
_CEIS_ROW = '"CEIS";"1";"J";"11222333000181";"EMPRESA SANCIONADA LTDA";"Impedimento"\r\n'


def _zip_bytes(csv_text: str, filename: str = "extract.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(filename, csv_text.encode("ISO-8859-1"))
    return buffer.getvalue()


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    monkeypatch.setattr(
        sanctions_source,
        "_build_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )


async def test_fetch_latest_parses_the_first_available_extract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_zip_bytes(_CEIS_HEADER + _CEIS_ROW))

    _patch_transport(monkeypatch, handler)

    result = PortalTransparenciaSanctionsSource().fetch_latest(SanctionsList.CEIS)

    assert result is not None
    extract_date, rows = result
    assert len(rows) == 1
    assert rows[0].document == "11222333000181"
    assert rows[0].name_normalized == "EMPRESA SANCIONADA LTDA"
    assert extract_date  # ISO date string


async def test_fetch_latest_searches_backward_when_recent_dates_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 4:
            return httpx.Response(403)
        return httpx.Response(200, content=_zip_bytes(_CEIS_HEADER + _CEIS_ROW))

    _patch_transport(monkeypatch, handler)

    result = PortalTransparenciaSanctionsSource(max_days_back=10).fetch_latest(SanctionsList.CEIS)

    assert result is not None
    assert calls["count"] == 4


async def test_fetch_latest_returns_none_when_nothing_found_in_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_transport(monkeypatch, lambda request: httpx.Response(403))

    result = PortalTransparenciaSanctionsSource(max_days_back=3).fetch_latest(SanctionsList.CEIS)

    assert result is None


async def test_oversized_download_is_treated_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security review (2026-09-29): defense-in-depth against a zip-bomb -- a response
    exceeding `_MAX_DOWNLOAD_BYTES` must abort, never be fully buffered."""
    monkeypatch.setattr(sanctions_source, "_MAX_DOWNLOAD_BYTES", 10)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_zip_bytes(_CEIS_HEADER + _CEIS_ROW))

    _patch_transport(monkeypatch, handler)

    result = PortalTransparenciaSanctionsSource(max_days_back=0).fetch_latest(SanctionsList.CEIS)

    assert result is None


async def test_row_count_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanctions_source, "_MAX_ROWS_PER_EXTRACT", 2)
    csv_text = _CEIS_HEADER + _CEIS_ROW * 5

    _patch_transport(
        monkeypatch, lambda request: httpx.Response(200, content=_zip_bytes(csv_text))
    )

    result = PortalTransparenciaSanctionsSource().fetch_latest(SanctionsList.CEIS)

    assert result is not None
    _, rows = result
    assert len(rows) == 2


async def test_cepim_uses_entity_shaped_field_names(monkeypatch: pytest.MonkeyPatch) -> None:
    cepim_csv = (
        '"CNPJ ENTIDADE";"NOME ENTIDADE";"NÚMERO CONVÊNIO";'
        '"ÓRGÃO CONCEDENTE";"MOTIVO DO IMPEDIMENTO"\r\n'
        '"22333444000199";"ONG IMPEDIDA";"123";"MINISTERIO X";"Prestacao de contas"\r\n'
    )
    _patch_transport(
        monkeypatch, lambda request: httpx.Response(200, content=_zip_bytes(cepim_csv))
    )

    result = PortalTransparenciaSanctionsSource().fetch_latest(SanctionsList.CEPIM)

    assert result is not None
    _, rows = result
    assert rows[0].document == "22333444000199"
    assert rows[0].name_normalized == "ONG IMPEDIDA"
