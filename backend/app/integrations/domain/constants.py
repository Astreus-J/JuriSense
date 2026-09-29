"""Integration configuration-record vocabulary (STORY-1.4.1) and the sanctions-source
vocabulary for the supplier verification adapters (STORY-2.5, ADR-017)."""

from enum import StrEnum


class IntegrationStatus(StrEnum):
    """Lifecycle of a configuration record — no real connector exists yet (FEATURE-1.4)."""

    CONFIGURED = "configured"
    ACTIVE = "active"
    DISABLED = "disabled"


class SanctionsList(StrEnum):
    """Brazilian sanctions/restriction lists published by Portal da Transparência open
    data (ADR-017) — CEIS, CNEP, CEPIM, per docs/03-domain/supplier-compliance.md."""

    CEIS = "CEIS"
    CNEP = "CNEP"
    CEPIM = "CEPIM"
