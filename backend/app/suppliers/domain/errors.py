class SupplierError(Exception):
    """Domain error for the Suppliers bounded context."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SupplierNotFoundError(SupplierError):
    def __init__(self) -> None:
        super().__init__("Supplier not found")


class InvalidTaxIdError(SupplierError):
    """SUP-001: the tax_id's shape can't be real for its jurisdiction (e.g. a CNPJ that
    fails the official checksum) -- a data-quality rejection, not a duplicate."""


class DuplicateSupplierError(SupplierError):
    """BR-SUP-002: tax_id + organization_id must be unique."""

    def __init__(self, tax_id: str) -> None:
        super().__init__(
            f"A supplier with tax_id '{tax_id}' is already registered in this organization"
        )
        self.tax_id = tax_id


class SupplierCheckNotFoundError(SupplierError):
    def __init__(self) -> None:
        super().__init__("Supplier check not found")


class SupplierProfileNotFoundError(SupplierError):
    """No SupplierProfile exists yet -- e.g. the initial SupplierCheck triggered on
    creation (SUP-002) is still running (Celery is async) or has not yet completed
    successfully."""

    def __init__(self) -> None:
        super().__init__(
            "No SupplierProfile yet -- the supplier's verification check has not "
            "completed successfully"
        )


class InvalidStatusTransitionError(SupplierError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class ApprovalRequiresCompletedCheckError(SupplierError):
    """BR-SUP-003: a Supplier cannot move to `approved` without at least one `completed`
    SupplierCheck newer than any open (unresolved) sanctions flag."""

    def __init__(self) -> None:
        super().__init__(
            "Cannot approve a supplier without a completed SupplierCheck newer than any "
            "open sanctions flag"
        )
