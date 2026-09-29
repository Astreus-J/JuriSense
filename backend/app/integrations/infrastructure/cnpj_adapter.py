"""CNPJ registry adapter (ADR-017) — one leg of `SupplierVerificationPort`.

Backed by BrasilAPI (`https://brasilapi.com.br/api/cnpj/v1/{cnpj}`), verified live on
2026-09-28: free, no API key, returns the full registry record needed for
`docs/03-domain/supplier-compliance.md`'s "Registry status" and "Corporate structure"
categories (`descricao_situacao_cadastral`, `razao_social`, `natureza_juridica`,
`data_inicio_atividade`, `capital_social`, `cnae_fiscal_descricao`, `qsa` partners, and
address fields). ReceitaWS (`https://receitaws.com.br/v1/cnpj/{cnpj}`) was verified live
too and is the documented fallback if BrasilAPI's free tier ever adds a gate (see
ADR-017) — not wired in by default, to keep one adapter, one contract.
"""

import logging

import httpx

from app.integrations.domain.ports import SourceResult

logger = logging.getLogger("jurisense.integrations.cnpj")

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _build_http_client() -> httpx.AsyncClient:
    """Test seam: monkeypatched in tests to return a client bound to
    `httpx.MockTransport`, the same pattern `app.identity.api.deps.get_email_sender`
    uses for swapping an infrastructure adapter under test."""
    return httpx.AsyncClient(timeout=_TIMEOUT)


class CnpjRegistryAdapter:
    """Looks up one CNPJ against BrasilAPI. Never raises for a network/timeout failure —
    reports `SourceResult(status="unavailable")` instead, per
    `docs/03-domain/supplier-compliance.md` step 3 ("a source that times out is recorded
    as source_status=unavailable")."""

    BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"

    def __init__(self, *, max_retries: int = 2) -> None:
        self._max_retries = max_retries

    async def fetch(self, tax_id: str) -> SourceResult:
        digits = "".join(ch for ch in tax_id if ch.isdigit())
        last_error: str = "unknown error"
        async with _build_http_client() as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.get(f"{self.BASE_URL}/{digits}")
                except httpx.HTTPError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    logger.warning(
                        "CNPJ registry lookup attempt %d/%d failed for %s: %s",
                        attempt + 1,
                        self._max_retries + 1,
                        digits,
                        exc,
                    )
                    continue

                if response.status_code == 200:
                    return SourceResult(source="cnpj_registry", status="ok", data=response.json())
                if response.status_code == 404:
                    # A real, answered lookup that found nothing registered — a
                    # meaningful "ok" result (registry_status normalizes to "unknown"
                    # downstream), not a source failure.
                    return SourceResult(
                        source="cnpj_registry", status="ok", data={"not_found": True}
                    )
                last_error = f"unexpected HTTP {response.status_code}"

        return SourceResult(
            source="cnpj_registry", status="unavailable", data={"error": last_error}
        )
