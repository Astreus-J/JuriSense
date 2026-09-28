"""Integration configuration-record vocabulary (STORY-1.4.1)."""

from enum import StrEnum


class IntegrationStatus(StrEnum):
    """Lifecycle of a configuration record — no real connector exists yet (FEATURE-1.4)."""

    CONFIGURED = "configured"
    ACTIVE = "active"
    DISABLED = "disabled"
