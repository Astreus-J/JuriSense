class EvidenceError(Exception):
    """Domain error for the Evidence & Audit bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EvidencePackageNotFoundError(EvidenceError):
    """Raised for a missing package AND for one belonging to another organization. The two
    cases are deliberately indistinguishable to the caller (ADR-003: never 403, never empty)."""

    def __init__(self) -> None:
        super().__init__("Evidence package not found")
