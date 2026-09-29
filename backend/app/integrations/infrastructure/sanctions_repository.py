from collections.abc import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.infrastructure.models import SanctionsEntry


class SanctionsRepository:
    """Reads/writes the local `sanctions_entries` index (ADR-017). Query methods here
    never make a network call — that happens only in `PortalTransparenciaSanctionsSource`,
    which `refresh_sanctions_index` (infrastructure/tasks.py) runs on a schedule."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_list(
        self, *, list_name: str, extract_date: str, entries: Iterable[SanctionsEntry]
    ) -> int:
        """Deletes every existing row for `list_name` and inserts the fresh extract, in
        the same transaction, so a reader never sees a half-replaced list."""
        await self._session.execute(
            delete(SanctionsEntry).where(SanctionsEntry.list_name == list_name)
        )
        count = 0
        for entry in entries:
            self._session.add(entry)
            count += 1
        await self._session.commit()
        return count

    async def has_data(self, *, list_name: str) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(SanctionsEntry)
            .where(SanctionsEntry.list_name == list_name)
        )
        return (result.scalar_one() or 0) > 0

    async def find_by_document(self, document: str) -> list[SanctionsEntry]:
        if not document:
            return []
        result = await self._session.execute(
            select(SanctionsEntry).where(SanctionsEntry.document == document)
        )
        return list(result.scalars())

    async def find_by_name(self, name_normalized: str) -> list[SanctionsEntry]:
        if not name_normalized:
            return []
        result = await self._session.execute(
            select(SanctionsEntry).where(SanctionsEntry.name_normalized == name_normalized)
        )
        return list(result.scalars())
