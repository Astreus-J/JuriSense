"""Concrete `SupplierVerificationPort` implementation (ADR-017): orchestrates the CNPJ
registry adapter and the sanctions adapter into one verification run. Only reachable from
other contexts through `app.integrations.application.supplier_verification_service` — see
`app/integrations/domain/ports.py` for why this lives in Integrations at all.
"""

from app.integrations.domain.ports import (
    SourceResult,
    SupplierVerificationPort,
    VerificationOutcome,
)
from app.integrations.infrastructure.cnpj_adapter import CnpjRegistryAdapter
from app.integrations.infrastructure.sanctions_adapter import SanctionsAdapter


def _responsible_party_names(registry_data: dict) -> list[str]:
    """Best-effort extraction of partner/representative names from a BrasilAPI-shaped
    registry payload (`qsa`) — see ADR-017 for why matching them is name-based."""
    names: list[str] = []
    for partner in registry_data.get("qsa") or []:
        name = partner.get("nome_socio")
        if name:
            names.append(name)
    return names


class SupplierVerificationAdapter(SupplierVerificationPort):
    def __init__(
        self, *, cnpj_adapter: CnpjRegistryAdapter, sanctions_adapter: SanctionsAdapter
    ) -> None:
        self._cnpj_adapter = cnpj_adapter
        self._sanctions_adapter = sanctions_adapter

    async def verify(
        self, *, tax_id: str, jurisdiction: str, legal_name: str
    ) -> VerificationOutcome:
        results: list[SourceResult] = []

        registry_result = await self._cnpj_adapter.fetch(tax_id)
        results.append(registry_result)

        responsible_parties = (
            _responsible_party_names(registry_result.data) if registry_result.status == "ok" else []
        )
        sanctions_result = await self._sanctions_adapter.check(
            tax_id=tax_id, responsible_party_names=responsible_parties
        )
        results.append(sanctions_result)

        return VerificationOutcome(
            sources_consulted=[result.source for result in results], results=results
        )
