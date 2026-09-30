class ContractsError(Exception):
    """Domain error for the Contracts & Documents bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentNotFoundError(ContractsError):
    def __init__(self) -> None:
        super().__init__("Document not found")


class ContractNotFoundError(ContractsError):
    def __init__(self) -> None:
        super().__init__("Contract not found")


class ContractVersionNotFoundError(ContractsError):
    def __init__(self) -> None:
        super().__init__("Contract version not found")


class UnsupportedFileTypeError(ContractsError):
    """SEC-003 / document-intelligence.md: the sniffed (not declared) type is not one of
    PDF/DOCX/TXT, or the sniffed type does not match the declared content-type/extension
    (type-spoofing)."""


class FileTooLargeError(ContractsError):
    def __init__(self, *, max_bytes: int) -> None:
        super().__init__(f"File exceeds the maximum allowed size of {max_bytes} bytes")
        self.max_bytes = max_bytes


class MalwareDetectedError(ContractsError):
    """SEC-003: the upload matched a known malicious signature (see
    `app.contracts.infrastructure.document_scanner` for the exact scope decision)."""


class SupplierMismatchError(ContractsError):
    """BR-CON-001: a Contract belongs to exactly one Supplier -- re-uploading a version
    against an existing contract_id with a different supplier_id is rejected rather than
    silently reassigning the contract."""


class InvalidSupplierReferenceError(ContractsError):
    """`Contract.supplier_id` is a plain foreign-key value, never a cross-context query
    (`docs/04-architecture/components.md` rule 2) -- an unknown supplier_id therefore
    only surfaces as a database FK-constraint violation, translated here into a domain
    error rather than a raw 500."""

    def __init__(self) -> None:
        super().__init__("supplier_id does not reference an existing supplier")


class MissingContractMetadataError(ContractsError):
    """Creating a *new* Contract (no `contract_id` given) requires `title` and
    `contract_type`; re-uploading against an existing `contract_id` does not."""


class InvalidClauseProvenanceError(ContractsError):
    """BR-CON-004: a Clause without a page/span citation cannot be constructed at all --
    enforced at construction time, not just at the database/API layer (see
    `app.contracts.infrastructure.models.Clause.__init__`)."""


class ContractVersionNotReadyForConfirmationError(ContractsError):
    """CON-005/BR-CON-003: confirmation only applies to a version currently awaiting it."""

    def __init__(self, current_status: str) -> None:
        super().__init__(
            f"ContractVersion is in status '{current_status}', not 'needs_confirmation' "
            "-- nothing to confirm"
        )
        self.current_status = current_status
