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
    """`supplier_id` doesn't resolve to a real supplier owned by the caller's own
    organization -- checked via `app.suppliers.application.supplier_service
    .supplier_belongs_to_organization` (an application-layer call, the rule-2-sanctioned
    way to reach Suppliers without a cross-context ORM query) before anything is
    created, plus the DB FK constraint as a defense-in-depth backstop for the race
    window between that check and the insert.

    Security review (2026-09-29): this previously only caught a *nonexistent*
    supplier_id via the FK constraint -- a real supplier belonging to a *different*
    organization satisfied that FK and was silently accepted. Deliberately reused for
    both "doesn't exist" and "belongs to another organization" (never a distinct
    error/message for the latter), matching this codebase's established avoid-
    existence-leak pattern for cross-tenant lookups elsewhere (e.g.
    `app.identity.application.user_service.get_user`)."""

    def __init__(self) -> None:
        super().__init__("supplier_id does not reference an existing supplier")


class ContractLimitExceededError(ContractsError):
    """Security audit (2026-10-12): per-organization resource-exhaustion backstop,
    checked in `contract_service.upload_contract_version` before a new `Contract` row is
    created -- unbounded Contracts is also unbounded cost (every uploaded version
    triggers a real AI extraction call), matching the #180 precedent for Policies."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"This organization has reached its limit of {limit} contracts")


class MissingContractMetadataError(ContractsError):
    """Creating a *new* Contract (no `contract_id` given) requires `title` and
    `contract_type`; re-uploading against an existing `contract_id` does not."""


class ConcurrentVersionConflictError(ContractsError):
    """QA review (2026-09-29): two simultaneous uploads against the same `contract_id`
    both computed the same next `version_number` before either committed; the DB unique
    index (`contract_id`, `version_number`) catches the losing insert, which used to
    surface as an unhandled 500 (no `IntegrityError` handler existed on this flush,
    unlike the equivalent handler on `Contract` creation just above it in
    `contract_service.upload_contract_version`). The client should simply retry the
    upload."""

    def __init__(self) -> None:
        super().__init__(
            "Another upload to this contract just completed -- retry to get the next "
            "version number"
        )


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
