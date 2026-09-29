"""Domain ports owned by Integrations (STORY-2.5, ADR-017).

`SupplierVerificationPort` is the contract `Suppliers` calls to run a `SupplierCheck`
against external sources. It lives here — not in `app/suppliers/` — because Integrations
is this codebase's seam for every external call (CLAUDE.md: "Integrations translates
external events into commands for the other contexts"); Suppliers is a consumer of the
contract, never its author. Concrete adapters (CNPJ registry, sanctions) live in
`app/integrations/infrastructure/`; `Suppliers` reaches them only through
`app/integrations/application/supplier_verification_service.py`, never by importing
`app.integrations.infrastructure` directly (enforced by
`tests/integrations/test_boundary_rules.py` and `tests/suppliers/test_boundary_rules.py`).
"""

from dataclasses import dataclass
from typing import Any, Protocol

# The two source categories `docs/03-domain/supplier-compliance.md` step 3 calls
# "mandatory" — if either is unavailable, the whole SupplierCheck must fail rather than
# complete looking clean.
MANDATORY_SOURCES = frozenset({"cnpj_registry", "sanctions"})


@dataclass(frozen=True)
class SourceResult:
    """One external source's contribution to a `SupplierCheck`'s `raw_results`."""

    source: str
    status: str  # "ok" | "unavailable"
    data: dict[str, Any]


@dataclass(frozen=True)
class VerificationOutcome:
    """Everything a `SupplierVerificationPort.verify()` call produces for one check."""

    sources_consulted: list[str]
    results: list[SourceResult]

    def any_mandatory_source_unavailable(self) -> bool:
        by_source = {result.source: result for result in self.results}
        return any(
            source not in by_source or by_source[source].status == "unavailable"
            for source in MANDATORY_SOURCES
        )

    def raw_results(self) -> dict[str, Any]:
        """Shape stored verbatim on `SupplierCheck.raw_results` (docs/03-domain/domain-model.md)."""
        return {
            result.source: {"status": result.status, "data": result.data} for result in self.results
        }


class SupplierVerificationPort(Protocol):
    """Runs one point-in-time verification for a supplier (SUP-002).

    Implementations must never raise for a source being down — an unreachable source is
    reported as a `SourceResult(status="unavailable")`, not an exception (an adapter-level
    bug or a truly unexpected error is the only thing that should still raise).
    """

    async def verify(
        self, *, tax_id: str, jurisdiction: str, legal_name: str
    ) -> VerificationOutcome: ...
