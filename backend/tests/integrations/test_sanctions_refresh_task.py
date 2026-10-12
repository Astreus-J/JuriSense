"""#141: `app/integrations/infrastructure/tasks.py`'s `refresh_sanctions_index`/
`_refresh_one_list`/`_refresh_all_lists` had zero test coverage before this -- every
dependency they orchestrate (`PortalTransparenciaSanctionsSource`, `SanctionsRepository`,
`SanctionsAdapter`) is unit-tested individually, but the task's own wiring, including
ADR-017's explicitly-flagged CEPIM "no extract found today, index left unchanged" path,
had no regression protection at the task level.

`task_session()` (`app/core/db.py`) deliberately creates its OWN fresh engine from
`Settings.database_url` on every call -- correct for a real Celery worker (a fresh event
loop per task invocation), but it means calling these functions directly in a test would
try to hit the real configured database, not the test's isolated SQLite instance. The
`patched_task_session` fixture below swaps it for one yielding from this test's own
`db_session_factory`, the same seam-swap shape `mock_openrouter`/`run_supplier_checks_inline`
use for their own external dependencies.
"""

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.integrations.domain.constants import SanctionsList
from app.integrations.infrastructure import tasks
from app.integrations.infrastructure.models import SanctionsEntry
from app.integrations.infrastructure.sanctions_source import SanctionsRow


@pytest.fixture
def patched_task_session(monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker):
    @asynccontextmanager
    async def _fake_task_session():
        async with db_session_factory() as session:
            yield session

    monkeypatch.setattr(tasks, "task_session", _fake_task_session)


def _row(document: str, name: str) -> SanctionsRow:
    return SanctionsRow(document=document, name_normalized=name, raw={"document": document})


async def _entries_for(
    db_session_factory: async_sessionmaker, list_name: str
) -> list[SanctionsEntry]:
    async with db_session_factory() as session:
        result = await session.execute(
            select(SanctionsEntry).where(SanctionsEntry.list_name == list_name)
        )
        return list(result.scalars())


async def test_refresh_one_list_populates_the_index_from_the_fetched_extract(
    patched_task_session, monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    def _fake_fetch_latest(self, list_name: SanctionsList):
        assert list_name is SanctionsList.CEIS
        return ("2026-10-12", [_row("11111111111", "ACME LTDA")])

    monkeypatch.setattr(
        "app.integrations.infrastructure.sanctions_source.PortalTransparenciaSanctionsSource"
        ".fetch_latest",
        _fake_fetch_latest,
    )

    count = await tasks._refresh_one_list(SanctionsList.CEIS)

    assert count == 1
    entries = await _entries_for(db_session_factory, SanctionsList.CEIS.value)
    assert len(entries) == 1
    assert entries[0].document == "11111111111"
    assert entries[0].extract_date == "2026-10-12"


async def test_refresh_one_list_leaves_the_index_unchanged_when_no_extract_is_found(
    patched_task_session, monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """ADR-017's explicitly-flagged CEPIM path: `fetch_latest` returning `None` (no
    extract published within the search window) must leave any existing index entries
    untouched, not wipe them -- `_refresh_one_list` returns early before calling
    `SanctionsRepository.replace_list` at all."""
    async with db_session_factory() as session:
        session.add(
            SanctionsEntry(
                list_name=SanctionsList.CEPIM.value,
                document="22222222222",
                name_normalized="PRE-EXISTING LTDA",
                raw={},
                extract_date="2026-10-01",
            )
        )
        await session.commit()

    def _fake_fetch_latest(self, list_name: SanctionsList):
        return None

    monkeypatch.setattr(
        "app.integrations.infrastructure.sanctions_source.PortalTransparenciaSanctionsSource"
        ".fetch_latest",
        _fake_fetch_latest,
    )

    count = await tasks._refresh_one_list(SanctionsList.CEPIM)

    assert count == 0
    entries = await _entries_for(db_session_factory, SanctionsList.CEPIM.value)
    assert len(entries) == 1
    assert entries[0].document == "22222222222"  # untouched


async def test_refresh_all_lists_handles_each_list_independently(
    patched_task_session, monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """One real extract (CEIS), one "not found today" (CNEP), one real extract (CEPIM) --
    each list's own outcome must not affect the others'."""

    def _fake_fetch_latest(self, list_name: SanctionsList):
        if list_name is SanctionsList.CNEP:
            return None
        return (
            "2026-10-12",
            [_row(f"{list_name.value}-doc", f"{list_name.value} SUPPLIER")],
        )

    monkeypatch.setattr(
        "app.integrations.infrastructure.sanctions_source.PortalTransparenciaSanctionsSource"
        ".fetch_latest",
        _fake_fetch_latest,
    )

    counts = await tasks._refresh_all_lists()

    assert counts == {"CEIS": 1, "CNEP": 0, "CEPIM": 1}
    assert len(await _entries_for(db_session_factory, "CEIS")) == 1
    assert len(await _entries_for(db_session_factory, "CNEP")) == 0
    assert len(await _entries_for(db_session_factory, "CEPIM")) == 1


async def test_refresh_one_list_replaces_rather_than_appends(
    patched_task_session, monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """A second refresh with a newer extract must replace the prior entries for that
    list, not accumulate alongside them (`SanctionsRepository.replace_list`'s own
    contract) -- the task-level wiring must actually call it, not just insert."""
    async with db_session_factory() as session:
        session.add(
            SanctionsEntry(
                list_name=SanctionsList.CEIS.value,
                document="33333333333",
                name_normalized="OLD ENTRY LTDA",
                raw={},
                extract_date="2026-09-01",
            )
        )
        await session.commit()

    def _fake_fetch_latest(self, list_name: SanctionsList):
        return ("2026-10-12", [_row("44444444444", "NEW ENTRY LTDA")])

    monkeypatch.setattr(
        "app.integrations.infrastructure.sanctions_source.PortalTransparenciaSanctionsSource"
        ".fetch_latest",
        _fake_fetch_latest,
    )

    await tasks._refresh_one_list(SanctionsList.CEIS)

    entries = await _entries_for(db_session_factory, SanctionsList.CEIS.value)
    assert len(entries) == 1
    assert entries[0].document == "44444444444"
