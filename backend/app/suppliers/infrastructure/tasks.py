"""Celery task running one `SupplierCheck` (SUP-002, STORY-2.4).

Enqueued via `app.suppliers.application.check_service.enqueue_supplier_check` — never
called directly from a route or another context. Synchronous (Celery tasks are), bridges
to the async application logic with `asyncio.run`, the same shape
`app.integrations.infrastructure.tasks.refresh_sanctions_index` uses.
"""

import asyncio
import logging
import uuid

from app.core.celery_app import celery_app
from app.core.db import get_sessionmaker

logger = logging.getLogger("jurisense.suppliers.tasks")


async def _run(check_id: str) -> None:
    # Imported inside the function, not at module level: `check_service` imports
    # `app.suppliers.infrastructure.tasks` lazily too (inside `enqueue_supplier_check`)
    # to break the natural application<->task-wrapper import cycle.
    from app.suppliers.application.check_service import run_supplier_check

    async with get_sessionmaker()() as session:
        await run_supplier_check(session, check_id=uuid.UUID(check_id))


@celery_app.task(
    name="suppliers.run_supplier_check", bind=True, max_retries=2, default_retry_delay=30
)
def run_supplier_check_task(self, check_id: str) -> None:
    try:
        asyncio.run(_run(check_id))
    except Exception as exc:  # noqa: BLE001 — Celery's own retry/failure bookkeeping needs this
        logger.exception("SupplierCheck %s task failed", check_id)
        raise self.retry(exc=exc) from exc
