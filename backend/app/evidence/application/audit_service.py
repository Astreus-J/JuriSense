"""Cross-context audit logging (STORY-0.3.1).

Other bounded contexts call `emit_audit_event` directly (an application-layer call, per
the coding-standards.md boundary rules — never a cross-context ORM import) whenever they
complete a state-changing action in the catalog (docs/03-domain/audit.md).
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.infrastructure.models import AuditEvent
from app.evidence.infrastructure.repositories import AuditEventRepository


async def emit_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    actor_id: uuid.UUID | None,
    organization_id: uuid.UUID | None,
    payload: dict[str, Any],
) -> AuditEvent:
    """Records one append-only AuditEvent.

    Does not commit the session — callers already commit as part of their own use-case
    transaction, matching the existing `repository.add()` pattern used throughout
    app/identity/ (the caller flushes first if it needs the referenced rows' generated
    ids for the payload, then commits once at the end of its use case).
    """
    event = AuditEvent(
        event_type=event_type,
        actor_id=actor_id,
        organization_id=organization_id,
        payload=payload,
    )
    AuditEventRepository(session).add(event)
    return event
