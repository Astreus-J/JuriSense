import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.integrations.domain.constants import IntegrationStatus


class Integration(Base):
    """A configuration record only — establishes the seam future connectors (DocuSign,
    Slack, webhooks — EPIC-9) will use, per STORY-1.4.1. No connector logic lives here yet.

    Per `docs/04-architecture/components.md` rule 8 ("Integrations must never write to
    Supplier/Contract/Policy/... tables") this table, and the rest of `app/integrations/`,
    is the *only* thing this bounded context is allowed to write to. See
    `tests/integrations/test_boundary_rules.py` for the automated check.
    """

    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    # Free-form provider identifier (e.g. "docusign", "slack") — not an enum yet, since no
    # concrete connector exists; the exact vocabulary is future-epic scope (EPIC-9).
    provider: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default=IntegrationStatus.CONFIGURED.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
