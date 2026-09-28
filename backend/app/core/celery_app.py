"""Minimal Celery instance, using Redis as broker and result backend (ADR-006).

This module does **not** define any real task yet -- that is future-epic
work, once each bounded context (Contracts & Documents, AI Services, etc.)
needs asynchronous processing (AI extraction, OCR, notifications, external
verification API calls). It exists only so that:

- the `celery-worker` service in `docker-compose.yml` has a valid Celery app
  to point at (`celery -A app.core.celery_app worker`);
- future tasks have a single place to register on (`@celery_app.task`),
  instead of each bounded context creating its own Celery app.

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
)
