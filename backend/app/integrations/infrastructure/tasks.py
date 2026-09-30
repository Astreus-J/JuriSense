"""Celery task refreshing the local sanctions index (ADR-017, STORY-2.5).

Registered on the shared `celery_app` (`app/core/celery_app.py`); the worker discovers it
via that module's `imports` config, not an import at module-load time here (avoids a
celery_app <-> tasks circular import).

This task is synchronous (Celery tasks are), so it bridges to the async SQLAlchemy stack
with `asyncio.run`, the same shape `app.suppliers.infrastructure.tasks` uses for
`run_supplier_check_task`.
"""

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.db import task_session
from app.integrations.domain.constants import SanctionsList
from app.integrations.infrastructure.models import SanctionsEntry
from app.integrations.infrastructure.sanctions_repository import SanctionsRepository
from app.integrations.infrastructure.sanctions_source import PortalTransparenciaSanctionsSource

logger = logging.getLogger("jurisense.integrations.tasks")


async def _refresh_one_list(list_name: SanctionsList) -> int:
    source = PortalTransparenciaSanctionsSource()
    fetched = await asyncio.to_thread(source.fetch_latest, list_name)
    if fetched is None:
        logger.warning(
            "No %s extract found within the search window — index left unchanged", list_name
        )
        return 0

    extract_date, rows = fetched
    entries = [
        SanctionsEntry(
            list_name=list_name.value,
            document=row.document,
            name_normalized=row.name_normalized,
            raw=row.raw,
            extract_date=extract_date,
        )
        for row in rows
    ]

    async with task_session() as session:
        count = await SanctionsRepository(session).replace_list(
            list_name=list_name.value, extract_date=extract_date, entries=entries
        )
    logger.info(
        "Refreshed %s: %d entries from extract dated %s", list_name.value, count, extract_date
    )
    return count


async def _refresh_all_lists() -> dict[str, int]:
    return {list_name.value: await _refresh_one_list(list_name) for list_name in SanctionsList}


@celery_app.task(name="integrations.refresh_sanctions_index")
def refresh_sanctions_index() -> dict[str, int]:
    """Downloads the most recent CEIS/CNEP/CEPIM bulk extract and replaces the local
    index (ADR-017). Intended to run on a schedule (exact cadence is a follow-up
    decision, alongside the still-TBD SupplierCheck re-check cadence in
    docs/03-domain/supplier-compliance.md); can also be triggered manually
    (`refresh_sanctions_index.delay()`) to populate a fresh environment's index for the
    first time.
    """
    return asyncio.run(_refresh_all_lists())
