import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
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


class SanctionsEntry(Base):
    """One row from a Brazilian sanctions/restriction list bulk extract (CEIS, CNEP or
    CEPIM — `SanctionsList`), locally indexed by `refresh_sanctions_index`
    (`app/integrations/infrastructure/tasks.py`) so `SanctionsAdapter` can answer a
    `SupplierCheck`'s sanctions leg without a live call per check (ADR-017: Portal da
    Transparência's live query API requires a registered API key we do not
    self-provision; its public bulk open-data extracts do not).

    Deliberately a **global** reference table, not tenant-scoped: sanctions lists are
    public, jurisdiction-wide facts, not per-organization data (see
    `docs/04-architecture/components.md` — only `Supplier`/`SupplierCheck`/
    `SupplierProfile`, which reference this table's matches, carry `organization_id`).

    Rows for one `list_name` are fully replaced (not accumulated) on each refresh, via
    `SanctionsRepository.replace_list` — the same "replace, don't accumulate" idea as
    `SupplierProfile`, applied to reference data instead of per-supplier data.
    """

    __tablename__ = "sanctions_entries"
    __table_args__ = (
        Index("ix_sanctions_entries_list_document", "list_name", "document"),
        Index("ix_sanctions_entries_list_name_normalized", "list_name", "name_normalized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    list_name: Mapped[str] = mapped_column(String(10), index=True)
    # Digits-only CPF/CNPJ of the sanctioned party, when the extract provides one.
    document: Mapped[str] = mapped_column(String(20), default="")
    # Uppercased, whitespace-normalized name — matched against a Supplier's legal_name
    # and, per ADR-017's documented CPF-masking limitation, against responsible-party
    # names (best-effort; CPFs for partners come masked from the CNPJ registry source).
    name_normalized: Mapped[str] = mapped_column(String(255), default="")
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    extract_date: Mapped[str] = mapped_column(String(10))  # ISO date of the source extract
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
