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


class BlockchainAnchorNotFoundError(EvidenceError):
    """FEATURE-8.2: raised for a missing BlockchainAnchor AND for one belonging to another
    organization -- same indistinguishable-404 contract as EvidencePackageNotFoundError."""

    def __init__(self) -> None:
        super().__init__("Blockchain anchor not found")


class AnchorAlreadySubmittedError(EvidenceError):
    """Raised by `anchoring_service.submit_anchor` when the EvidencePackage already has a
    BlockchainAnchor (one anchor per package, per `uq_blockchain_anchors_one_per_package`) --
    a concurrent-submission backstop, the same role `DecisionAlreadyExistsError` plays for its
    own unique constraint."""

    def __init__(self) -> None:
        super().__init__("This evidence package has already been submitted for anchoring")


class AnchoringProviderError(EvidenceError):
    """Raised when a concrete `AnchoringProvider` adapter cannot complete a call -- a network
    failure, a non-2xx response, or a response that doesn't match the provider's own documented
    shape. Never raised for a legitimate "not found"/"not yet confirmed" outcome, which the
    provider methods report through their own return values instead (`AnchorProof`/`bool`)."""
