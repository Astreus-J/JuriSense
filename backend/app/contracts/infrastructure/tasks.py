"""Celery task running one `ContractVersion`'s AI extraction (CON-003).

Enqueued via `app.contracts.application.extraction_orchestration.enqueue_contract_extraction`
-- never called directly. Mirrors `app.suppliers.infrastructure.tasks`'s shape exactly.
"""

import asyncio
import logging
import uuid

from app.core.celery_app import celery_app
from app.core.db import task_session

logger = logging.getLogger("jurisense.contracts.tasks")


async def _run(contract_version_id: str) -> None:
    from app.contracts.application.extraction_orchestration import run_extraction_for_version

    async with task_session() as session:
        await run_extraction_for_version(
            session, contract_version_id=uuid.UUID(contract_version_id)
        )


@celery_app.task(
    name="contracts.run_contract_extraction", bind=True, max_retries=2, default_retry_delay=30
)
def run_contract_extraction_task(self, contract_version_id: str) -> None:
    try:
        asyncio.run(_run(contract_version_id))
    except Exception as exc:  # noqa: BLE001 — Celery's own retry/failure bookkeeping needs this
        logger.exception("ContractVersion %s extraction task failed", contract_version_id)
        raise self.retry(exc=exc) from exc
