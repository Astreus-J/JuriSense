"""Shared helpers for Suppliers tests: RBAC header bootstrapping, mocking the CNPJ
registry HTTP call, and seeding the local sanctions index — all so the check-flow tests
never touch the real network (ADR-017's adapters are hermetic-by-design at the query
layer; only the manually-verified live calls documented in ADR-017 hit the real internet).
"""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.integrations.infrastructure import cnpj_adapter
from app.integrations.infrastructure.models import SanctionsEntry
from app.integrations.infrastructure.sanctions_repository import SanctionsRepository

# Security audit (2026-10-12): `SanctionsAdapter.check` now also rejects a stale index
# (`Settings.sanctions_max_age_seconds`) -- a fixed past date here would eventually
# (and non-obviously) start failing every test that seeds "fresh" sanctions data as
# real time passes. "Today" keeps this fixture's own intent (a just-refreshed index)
# true regardless of when the suite actually runs.
_SEEDED_EXTRACT_DATE = datetime.now(UTC).date().isoformat()

ACTIVE_CNPJ_RESPONSE = {
    "cnpj": "00000000000191",
    "razao_social": "BANCO DO BRASIL SA",
    "descricao_situacao_cadastral": "ATIVA",
    "natureza_juridica": "Sociedade de Economia Mista",
    "data_inicio_atividade": "1966-08-01",
    "capital_social": 120000000000,
    "cnae_fiscal": "6422100",
    "cnae_fiscal_descricao": "Bancos múltiplos, com carteira comercial",
    "cnaes_secundarios": [],
    "logradouro": "SAUN QUADRA 5",
    "numero": "SN",
    "bairro": "ASA NORTE",
    "municipio": "BRASILIA",
    "uf": "DF",
    "cep": "70040912",
    "qsa": [{"nome_socio": "ALAN CARLOS GUEDES DE OLIVEIRA", "qualificacao_socio": "Diretor"}],
}


@pytest.fixture
def mock_cnpj_registry(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Returns `apply(data=..., status_code=200)` / `apply(unavailable=True)` to control
    what `CnpjRegistryAdapter.fetch` sees, without any real HTTP call."""

    def apply(
        *, data: dict | None = None, status_code: int = 200, unavailable: bool = False
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if unavailable:
                raise httpx.ConnectTimeout("simulated timeout", request=request)
            return httpx.Response(
                status_code, json=data if data is not None else ACTIVE_CNPJ_RESPONSE
            )

        def build_client() -> httpx.AsyncClient:
            return httpx.AsyncClient(transport=httpx.MockTransport(handler))

        monkeypatch.setattr(cnpj_adapter, "_build_http_client", build_client)

    return apply


@pytest.fixture
def seed_sanctions_index(db_session_factory: async_sessionmaker) -> Callable:
    """Seeds `sanctions_entries` directly (bypassing the real bulk-download source,
    which has its own isolated tests) so `SanctionsAdapter` reports `status="ok"`
    instead of `"unavailable"`, optionally with a hit by document or by name."""

    async def seed(
        *,
        list_names: tuple[str, ...] = ("CEIS", "CNEP", "CEPIM"),
        hit_document: str | None = None,
        hit_name: str | None = None,
    ) -> None:
        async with db_session_factory() as session:
            repo = SanctionsRepository(session)
            for list_name in list_names:
                entries = []
                if list_name == "CEIS" and hit_document:
                    entries.append(
                        SanctionsEntry(
                            list_name=list_name,
                            document=hit_document,
                            name_normalized=hit_name or "",
                            raw={"seeded": True},
                            extract_date=_SEEDED_EXTRACT_DATE,
                        )
                    )
                elif list_name == "CEIS" and hit_name:
                    entries.append(
                        SanctionsEntry(
                            list_name=list_name,
                            document="",
                            name_normalized=hit_name,
                            raw={"seeded": True},
                            extract_date=_SEEDED_EXTRACT_DATE,
                        )
                    )
                else:
                    # A placeholder row so has_data() is True (index "refreshed") without
                    # introducing a hit for this list.
                    entries.append(
                        SanctionsEntry(
                            list_name=list_name,
                            document="00000000000",
                            name_normalized="PLACEHOLDER NON MATCHING ENTRY",
                            raw={"seeded": True},
                            extract_date=_SEEDED_EXTRACT_DATE,
                        )
                    )
                await repo.replace_list(
                    list_name=list_name, extract_date=_SEEDED_EXTRACT_DATE, entries=entries
                )

    return seed


async def register_org_and_login(
    client: httpx.AsyncClient, email: str, *, plan: str = "business"
) -> dict:
    await client.post(
        "/api/auth/register",
        json={
            "organization_name": f"Org of {email}",
            "full_name": "Admin",
            "email": email,
            "password": "StrongPass1",
            "plan": plan,
        },
    )
    login = await client.post("/api/auth/login", json={"email": email, "password": "StrongPass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
