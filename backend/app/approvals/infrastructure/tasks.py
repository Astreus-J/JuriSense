"""Celery task expiring stale `ApprovalRequest`s past their SLA (BR-APR-003,
STORY-6.2.3, ADR-006: time-based transitions are a Celery task's job, never the FastAPI
request session's).

Registered on the shared `celery_app` (`app/core/celery_app.py`); the worker discovers it
via that module's `imports` config, not an import at module-load time here -- same shape
`app.suppliers.infrastructure.tasks`/`app.integrations.infrastructure.tasks` use.
"""

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.db import task_session

logger = logging.getLogger("jurisense.approvals.tasks")


async def _expire_stale_requests() -> int:
    # Imported inside the function (not at module level) to mirror
    # `app.suppliers.infrastructure.tasks`'s own documented reason: breaks the natural
    # application<->task-wrapper import cycle.
    from app.approvals.application.sla_service import expire_stale_approval_requests

    async with task_session() as session:
        return await expire_stale_approval_requests(session)


@celery_app.task(name="approvals.expire_stale_approval_requests")
def expire_stale_approval_requests_task() -> int:
    """Intended to run on a schedule (exact cadence TBD, same as the sanctions-index
    refresh task); can also be triggered manually
    (`expire_stale_approval_requests_task.delay()`). Returns the count of requests
    expired, for operational visibility in Celery's own result backend/logs."""
    count = asyncio.run(_expire_stale_requests())
    logger.info("Expired %d stale approval request(s)", count)
    return count


async def _reevaluate_stale_decisions() -> int:
    # Imported inside the function for the same cycle-breaking reason as
    # `_expire_stale_requests` above.
    from app.approvals.application.reevaluation_service import reevaluate_stale_decisions

    async with task_session() as session:
        return await reevaluate_stale_decisions(session)


@celery_app.task(name="approvals.reevaluate_stale_decisions")
def reevaluate_stale_decisions_task() -> int:
    """FEATURE-6.4 (BR-DEC-004): scheduled by Celery beat at
    `settings.decision_reevaluation_interval_seconds` (see `app.core.celery_app`). Returns
    how many stale Decisions were re-evaluated in this run."""
    count = asyncio.run(_reevaluate_stale_decisions())
    logger.info("Re-evaluated %d stale decision(s)", count)
    return count
