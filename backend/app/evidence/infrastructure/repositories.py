import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.infrastructure.models import AuditEvent


class AuditEventRepository:
    """Append-only repository for AuditEvent.

    Intentionally exposes only `add`/`get`/`list` — no `update` or `delete` method exists
    anywhere on this class. This is the enforcement mechanism for BR-EVD-003/AUD-002: no
    actor, including Admin/Auditor roles, has any path to modify or remove a recorded
    event (see tests/evidence/test_audit_event.py's negative test).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: AuditEvent) -> None:
        self._session.add(event)

    async def get(self, event_id: uuid.UUID) -> AuditEvent | None:
        """Fetch a single event by id, unscoped by organization.

        No route calls this yet. Whoever adds the first one (EPIC-7, Evidence & Audit)
        MUST add its own organization_id check on the result before returning it to a
        caller -- `list()` already enforces tenant scoping, this method deliberately does
        not, since a single-event lookup's caller-side scoping needs depend on that
        route's own authorization shape.
        """
        return await self._session.get(AuditEvent, event_id)

    async def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).order_by(AuditEvent.occurred_at)
        if organization_id is not None:
            query = query.where(AuditEvent.organization_id == organization_id)
        if event_type is not None:
            query = query.where(AuditEvent.event_type == event_type)
        result = await self._session.execute(query)
        return list(result.scalars())
