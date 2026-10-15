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

The model imports at the very top (unrelated to the task-registration concern above --
these run eagerly, at this module's own import time) are a separate, real bug fix from
load testing the actual running worker (2026-10-14): no task module imports
`app.identity`, so `Base.metadata` never registered `User`/`Organization` inside a real
worker process, and any table with a FK to `users` (e.g. `documents.uploaded_by`) failed
SQLAlchemy's FK-target resolution the first time a task touched it --
`contracts.run_contract_extraction` retried every 30s forever rather than ever
succeeding. Invisible to the test suite (`conftest.py` always imports every context's
models explicitly, regardless of which task is under test); only visible running the
real worker end to end. Mirrors `app.main`'s own "import every context so the full
router/model graph is registered" pattern, applied here so a worker process is correct
independently of which task happens to run first.
"""

from celery import Celery
from celery.signals import worker_ready

import app.approvals.infrastructure.models  # noqa: F401
import app.contracts.infrastructure.models  # noqa: F401
import app.evidence.infrastructure.models  # noqa: F401
import app.identity.infrastructure.models  # noqa: F401
import app.integrations.infrastructure.models  # noqa: F401
import app.policies.infrastructure.models  # noqa: F401
import app.suppliers.infrastructure.models  # noqa: F401
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


@worker_ready.connect
def _run_sanctions_refresh_on_startup(**_kwargs: object) -> None:
    """Load testing (2026-10-14): a plain-interval `beat_schedule` entry does NOT run
    on beat's own startup -- confirmed empirically (the 900s approval-expiry sweep's
    first real run only fired 15 real minutes after `beat: Starting...`, not
    immediately). For `sanctions_refresh_interval_seconds` (24h), that means a freshly
    started environment has a completely empty sanctions index -- and sanctions is a
    MANDATORY source (`SanctionsAdapter`'s own docstring), so every single supplier
    check fails with "mandatory source unavailable" for up to a full day after any
    restart, confirmed live against this exact dev environment.
    `approvals.expire_stale_approval_requests`/`reevaluate_stale_decisions` don't get
    the same treatment: a few extra minutes/hours before their own first sweep is a
    minor staleness window, not a hard failure of an otherwise-working feature, so
    there's no need to short the same gap for them.

    Dispatches by task name (`send_task`) rather than importing `refresh_sanctions_index`
    directly -- `app/core` is shared-kernel wiring, not a caller reaching into a bounded
    context's internals (`tests/integrations/test_boundary_rules.py`), and `send_task`
    needs no import at all since the task is already registered via `imports` above.
    """
    celery_app.send_task("integrations.refresh_sanctions_index")
