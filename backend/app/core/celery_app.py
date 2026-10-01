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
    ),
)
