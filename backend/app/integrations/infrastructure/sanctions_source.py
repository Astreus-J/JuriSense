"""Sanctions bulk-extract downloader (ADR-017).

Portal da Transparência's live query API requires a registered API key (`chave-api-dados`
header) — verified live on 2026-09-28 (`HTTP 401`, "Chave de API não informada!"). This
module instead downloads the public, keyless bulk open-data extracts CEIS/CNEP/CEPIM
publish at `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/...`,
verified live the same day by actually downloading and parsing real files (see ADR-017).

Publish cadence differs per dataset — CEIS/CNEP appeared to publish daily, CEPIM more
sparsely (no file for several consecutive days, then one appears) — so this always
searches backward from today for the most recent available extract, rather than assuming
"today's file exists".
"""

import csv
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.integrations.domain.constants import SanctionsList

logger = logging.getLogger("jurisense.integrations.sanctions")

BASE_URL = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida"

# Security review (2026-09-29): defense-in-depth against a zip-bomb from a compromised or
# intercepted CGU endpoint -- no guard existed against either an outsized download or an
# outsized decompressed row count. ADR-017's own live verification found real extracts run
# ~3.4 MB (CEIS) with ~23,700 rows; these caps give generous headroom (~15x) while still
# bounding the worst case instead of leaving it fully unbounded.
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
_MAX_ROWS_PER_EXTRACT = 500_000

# Field names differ slightly per dataset (verified live 2026-09-28, ADR-017): CEIS/CNEP
# use "CPF OU CNPJ DO SANCIONADO" / "NOME DO SANCIONADO"; CEPIM uses the entity-shaped
# "CNPJ ENTIDADE" / "NOME ENTIDADE" instead. Checked in order, first match wins.
_DOCUMENT_FIELDS = ("CPF OU CNPJ DO SANCIONADO", "CNPJ ENTIDADE")
_NAME_FIELDS = (
    "NOME DO SANCIONADO",
    "NOME ENTIDADE",
    "NOME INFORMADO PELO ÓRGÃO SANCIONADOR",
    "RAZÃO SOCIAL - CADASTRO RECEITA",
)


def _build_http_client() -> httpx.Client:
    """Test seam, mirroring `cnpj_adapter._build_http_client` — monkeypatched in tests
    to a client bound to `httpx.MockTransport`. Synchronous client: this runs inside the
    synchronous Celery task (`infrastructure/tasks.py`), not the request/response cycle."""
    return httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))


def _digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _normalize_name(value: str | None) -> str:
    return " ".join((value or "").split()).strip().upper()


def _extract_field(record: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for key in candidates:
        if record.get(key):
            return record[key]
    return None


@dataclass(frozen=True)
class SanctionsRow:
    document: str
    name_normalized: str
    raw: dict[str, Any]


class PortalTransparenciaSanctionsSource:
    """Fetches and parses the most recent CEIS/CNEP/CEPIM bulk extract."""

    def __init__(self, *, max_days_back: int = 60) -> None:
        self._max_days_back = max_days_back

    def fetch_latest(self, list_name: SanctionsList) -> tuple[str, list[SanctionsRow]] | None:
        """Returns `(extract_date_iso, rows)` for the newest extract found, or `None` if
        nothing was found within `max_days_back` days (the caller treats that the same
        way as any other unavailable mandatory source)."""
        today = datetime.now(UTC).date()
        with _build_http_client() as client:
            for offset in range(self._max_days_back + 1):
                day = today - timedelta(days=offset)
                stamp = day.strftime("%Y%m%d")
                url = f"{BASE_URL}/{list_name.value.lower()}/{stamp}_{list_name.value}.zip"
                try:
                    content = self._download_capped(client, url)
                except httpx.HTTPError as exc:
                    logger.warning("Sanctions extract fetch failed for %s: %s", url, exc)
                    continue
                if content is None:
                    continue
                rows = self._parse_zip(content)
                logger.info(
                    "Loaded %d %s rows from extract dated %s", len(rows), list_name.value, stamp
                )
                return day.isoformat(), rows
        return None

    def _download_capped(self, client: httpx.Client, url: str) -> bytes | None:
        """Streams the response instead of buffering it whole via `.get()`, so a
        compromised/intercepted upstream can't force an unbounded in-memory download
        regardless of what it claims via `Content-Length` (security review, 2026-09-29).
        Returns `None` for a non-200 status or an oversized body, both treated the same as
        "no extract available today" by the caller."""
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                return None
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > _MAX_DOWNLOAD_BYTES:
                    logger.warning(
                        "Sanctions extract at %s exceeded %d bytes -- aborting download",
                        url,
                        _MAX_DOWNLOAD_BYTES,
                    )
                    return None
                chunks.append(chunk)
            return b"".join(chunks)

    def _parse_zip(self, content: bytes) -> list[SanctionsRow]:
        rows: list[SanctionsRow] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            for csv_name in csv_names:
                with archive.open(csv_name) as raw_file:
                    # Verified live 2026-09-28: these extracts are ISO-8859-1 (Latin-1)
                    # encoded, semicolon-delimited, with CRLF line endings.
                    text_stream = io.TextIOWrapper(raw_file, encoding="ISO-8859-1", newline="")
                    reader = csv.DictReader(text_stream, delimiter=";")
                    for record in reader:
                        if len(rows) >= _MAX_ROWS_PER_EXTRACT:
                            logger.warning(
                                "Sanctions extract %s exceeded %d rows -- truncating",
                                csv_name,
                                _MAX_ROWS_PER_EXTRACT,
                            )
                            break
                        document = _digits_only(_extract_field(record, _DOCUMENT_FIELDS))
                        name = _normalize_name(_extract_field(record, _NAME_FIELDS))
                        if not document and not name:
                            continue
                        rows.append(
                            SanctionsRow(document=document, name_normalized=name, raw=record)
                        )
        return rows
