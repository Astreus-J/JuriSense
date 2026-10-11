"""Celery task auto-submitting a Decision's EvidencePackage for anchoring (FEATURE-8.2, #199).

Enqueued via `app.evidence.application.anchoring_service.enqueue_anchor_submission` -- never
called directly from a route or another context. Mirrors
`app.suppliers.infrastructure.tasks.run_supplier_check_task`'s exact shape (synchronous Celery
task bridging to async application logic via `asyncio.run`), with ONE deliberate difference:
no automatic retry (see `submit_anchor_task`'s own docstring).
"""

import asyncio
import logging
import uuid

from app.core.celery_app import celery_app
from app.core.db import task_session
from app.evidence.domain.errors import AnchorAlreadySubmittedError

logger = logging.getLogger("jurisense.evidence.tasks")


async def _run(decision_id: str, organization_id: str, actor_id: str | None) -> None:
    # Imported inside the function, not at module level: `anchoring_service` imports this
    # module lazily too (inside `enqueue_anchor_submission`), to break the natural
    # application<->task-wrapper import cycle -- same shape as `check_service`/
    # `app.suppliers.infrastructure.tasks`.
    from app.evidence.application import anchoring_service, evidence_package_service

    async with task_session() as session:
        package_view = await evidence_package_service.get_package_for_decision(
            session,
            organization_id=uuid.UUID(organization_id),
            decision_id=uuid.UUID(decision_id),
        )
        try:
            await anchoring_service.submit_anchor(
                session,
                organization_id=uuid.UUID(organization_id),
                evidence_package_id=package_view.package.id,
                actor_id=uuid.UUID(actor_id) if actor_id is not None else None,
            )
        except AnchorAlreadySubmittedError:
            # Not a failure: a manual POST /evidence-packages/{id}/anchor (or a retried,
            # previously-successful run of this same task) already claimed this package --
            # the one outcome this task exists to guarantee ("this package is submitted")
            # is already true.
            logger.info(
                "Decision %s's package was already submitted for anchoring; skipping", decision_id
            )


@celery_app.task(name="evidence.submit_anchor")
def submit_anchor_task(decision_id: str, organization_id: str, actor_id: str | None) -> None:
    """Security review (2026-10-11): deliberately NOT retried, unlike every other task in
    this module's family (`run_supplier_check_task`, etc). `submit_anchor` calls a real,
    non-idempotent external provider (`provider.submit_hash` -- confirmed generating a fresh
    random id on every call, no dedup key); if anything fails AFTER that call succeeds but
    BEFORE this task's own transaction commits, the placeholder `BlockchainAnchor` row never
    becomes durable, so a blind retry would re-submit to the provider a second time -- a real,
    possibly billable duplicate, not just a wasted retry. Re-running a supplier check or a
    sanctions-index refresh has no such consequence, which is why those DO retry. A failure
    here is logged and left un-anchored; the package stays submittable later through the
    existing manual endpoint (`POST /evidence-packages/{id}/anchor`) once whatever caused the
    failure (a network blip, a misconfigured provider) is resolved -- recoverable, same as any
    Decision created before this feature existed."""
    try:
        asyncio.run(_run(decision_id, organization_id, actor_id))
    except Exception:
        logger.exception("Automatic anchor submission failed for decision %s", decision_id)
