"""Minimal Celery instance, using Redis as broker and result backend (ADR-006).

Real tasks started arriving with EPIC-2 (Supplier Intelligence): `app.suppliers.
infrastructure.tasks` (`run_supplier_check_task`) and `app.integrations.infrastructure.
tasks` (`refresh_sanctions_index`). Task modules are registered via `imports` below
rather than imported directly at the top of this module, so that:

- the `celery-worker` service in `docker-compose.yml` has a valid Celery app
  to point at (`celery -A app.core.celery_app worker`);
- task modules can import `celery_app` from here (`from app.core.celery_app import
  celery_app`) without a circular import, since Celery only imports them once the app
  is fully constructed (worker start time), not at this module's own import time.

Redis is already provisioned in `docker-compose.yml`; no new infrastructure
is required beyond it (see ADR-006 -- Celery + Redis, not a dedicated
workflow engine).
"""

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "jurisense",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    imports=(
        "app.suppliers.infrastructure.tasks",
        "app.integrations.infrastructure.tasks",
        "app.contracts.infrastructure.tasks",
        "app.approvals.infrastructure.tasks",
        "app.evidence.infrastructure.tasks",
    ),
    # FEATURE-6.4 (BR-DEC-004): the staleness sweep. Cadence is a TBD placeholder, see
    # settings.decision_reevaluation_interval_seconds.
    beat_schedule={
        "approvals-reevaluate-stale-decisions": {
            "task": "approvals.reevaluate_stale_decisions",
            "schedule": _settings.decision_reevaluation_interval_seconds,
        },
        "approvals-expire-stale-approval-requests": {
            "task": "approvals.expire_stale_approval_requests",
            "schedule": _settings.approval_expiry_sweep_interval_seconds,
        },
        # Security audit (2026-10-12): `refresh_sanctions_index` existed but was never
        # scheduled -- see `Settings.sanctions_refresh_interval_seconds`'s own docstring.
        "integrations-refresh-sanctions-index": {
            "task": "integrations.refresh_sanctions_index",
            "schedule": _settings.sanctions_refresh_interval_seconds,
        },
    },
)
