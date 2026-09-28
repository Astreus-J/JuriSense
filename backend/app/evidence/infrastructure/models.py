import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditEvent(Base):
    """Append-only log of every meaningful domain action (docs/03-domain/audit.md).

    `actor_id`/`organization_id` are plain UUID columns, not foreign keys: per
    docs/03-domain/domain-model.md, AuditEvent "references any other entity by id in
    payload" rather than through a DB-level relationship — the audit trail must remain
    resolvable even if the referenced row is later changed or removed. No update or
    delete path exists anywhere for this entity (BR-EVD-003/AUD-002); see
    AuditEventRepository, which exposes only add/get/list.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(default=None, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
