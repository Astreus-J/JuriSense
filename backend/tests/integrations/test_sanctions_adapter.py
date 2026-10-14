"""STORY-2.5: `SanctionsAdapter` — DB-backed, no network. Covers the "index never
refreshed" -> unavailable path (mandatory-source semantics), document-based hits, and
name-based responsible-party hits (the documented CPF-masking limitation, ADR-017).
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.integrations.infrastructure.models import SanctionsEntry
from app.integrations.infrastructure.sanctions_adapter import SanctionsAdapter
from app.integrations.infrastructure.sanctions_repository import SanctionsRepository

# Security audit (2026-10-12): `SanctionsAdapter.check` now also rejects a stale index
# (`Settings.sanctions_max_age_seconds`) -- "today" keeps these fixtures' own intent (a
# just-refreshed index) true regardless of when the suite actually runs.
_FRESH_EXTRACT_DATE = datetime.now(UTC).date().isoformat()


async def test_reports_unavailable_when_index_never_refreshed(
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        adapter = SanctionsAdapter(SanctionsRepository(session))
        result = await adapter.check(tax_id="00000000000191", responsible_party_names=[])

    assert result.status == "unavailable"


async def test_hit_by_document(db_session_factory: async_sessionmaker) -> None:
    async with db_session_factory() as session:
        repo = SanctionsRepository(session)
        for list_name in ("CEIS", "CNEP", "CEPIM"):
            if list_name == "CEIS":
                entries = [
                    SanctionsEntry(
                        list_name=list_name,
                        document="00000000000191",
                        name_normalized="BANCO DO BRASIL SA",
                        raw={},
                        extract_date=_FRESH_EXTRACT_DATE,
                    )
                ]
            else:
                # A refreshed-but-empty list still counts as "available" — has_data()
                # only asks "has this list ever been indexed", not "does it have a hit".
                entries = [
                    SanctionsEntry(
                        list_name=list_name,
                        document="",
                        name_normalized="PLACEHOLDER NON MATCHING ENTRY",
                        raw={},
                        extract_date=_FRESH_EXTRACT_DATE,
                    )
                ]
            await repo.replace_list(
                list_name=list_name, extract_date=_FRESH_EXTRACT_DATE, entries=entries
            )

        adapter = SanctionsAdapter(repo)
        result = await adapter.check(tax_id="00.000.000/0001-91", responsible_party_names=[])

    assert result.status == "ok"
    assert len(result.data["hits"]) == 1
    assert result.data["hits"][0]["matched_on"] == "tax_id"


async def test_hit_by_responsible_party_name(db_session_factory: async_sessionmaker) -> None:
    async with db_session_factory() as session:
        repo = SanctionsRepository(session)
        for list_name in ("CEIS", "CNEP", "CEPIM"):
            if list_name == "CEIS":
                entries = [
                    SanctionsEntry(
                        list_name=list_name,
                        document="",
                        name_normalized="ALAN CARLOS GUEDES DE OLIVEIRA",
                        raw={},
                        extract_date=_FRESH_EXTRACT_DATE,
                    )
                ]
            else:
                entries = [
                    SanctionsEntry(
                        list_name=list_name,
                        document="",
                        name_normalized="PLACEHOLDER NON MATCHING ENTRY",
                        raw={},
                        extract_date=_FRESH_EXTRACT_DATE,
                    )
                ]
            await repo.replace_list(
                list_name=list_name, extract_date=_FRESH_EXTRACT_DATE, entries=entries
            )

        adapter = SanctionsAdapter(repo)
        result = await adapter.check(
            tax_id="00000000000191",
            responsible_party_names=["Alan Carlos Guedes de Oliveira"],
        )

    assert result.status == "ok"
    assert len(result.data["hits"]) == 1
    assert result.data["hits"][0]["matched_on"] == "responsible_party"


async def test_reports_unavailable_when_the_index_has_gone_stale(
    db_session_factory: async_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Security audit (2026-10-12): a list that was refreshed once, long ago, and never
    again (no scheduled cadence existed before this audit) must never be reported as a
    clean "ok" -- confirmed by seeding a genuinely old `extract_date` and a tight
    `sanctions_max_age_seconds`, rather than asserting against the real default."""
    monkeypatch.setattr(get_settings(), "sanctions_max_age_seconds", 86_400)  # 1 day

    async with db_session_factory() as session:
        repo = SanctionsRepository(session)
        for list_name in ("CEIS", "CNEP", "CEPIM"):
            await repo.replace_list(
                list_name=list_name,
                extract_date="2020-01-01",
                entries=[
                    SanctionsEntry(
                        list_name=list_name,
                        document="",
                        name_normalized="PLACEHOLDER NON MATCHING ENTRY",
                        raw={},
                        extract_date="2020-01-01",
                    )
                ],
            )

        adapter = SanctionsAdapter(repo)
        result = await adapter.check(tax_id="00000000000191", responsible_party_names=[])

    assert result.status == "unavailable"
    assert "stale" in result.data["reason"]


async def test_no_hit_when_nothing_matches(db_session_factory: async_sessionmaker) -> None:
    async with db_session_factory() as session:
        repo = SanctionsRepository(session)
        for list_name in ("CEIS", "CNEP", "CEPIM"):
            await repo.replace_list(
                list_name=list_name,
                extract_date=_FRESH_EXTRACT_DATE,
                entries=[
                    SanctionsEntry(
                        list_name=list_name,
                        document="99999999999999",
                        name_normalized="SOMEONE ELSE",
                        raw={},
                        extract_date=_FRESH_EXTRACT_DATE,
                    )
                ],
            )

        adapter = SanctionsAdapter(repo)
        result = await adapter.check(tax_id="00000000000191", responsible_party_names=["Nobody"])

    assert result.status == "ok"
    assert result.data["hits"] == []
