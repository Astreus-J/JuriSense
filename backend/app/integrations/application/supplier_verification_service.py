"""Application-layer seam `Suppliers` calls to run a `SupplierCheck` (STORY-2.5).

Mirrors `app.evidence.application.audit_service.emit_audit_event`: other bounded contexts
call a plain application-layer function here, never `app.integrations.infrastructure`
directly (enforced by `tests/integrations/test_boundary_rules.py` and
`tests/suppliers/test_boundary_rules.py`). See `app/integrations/domain/ports.py` for why
`SupplierVerificationPort` is owned by Integrations rather than Suppliers.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.domain.ports import SupplierVerificationPort
from app.integrations.infrastructure.cnpj_adapter import CnpjRegistryAdapter
from app.integrations.infrastructure.sanctions_adapter import SanctionsAdapter
from app.integrations.infrastructure.sanctions_repository import SanctionsRepository
from app.integrations.infrastructure.supplier_verification_adapter import (
    SupplierVerificationAdapter,
)


def get_supplier_verification_port(session: AsyncSession) -> SupplierVerificationPort:
    """Builds the current `SupplierVerificationPort` implementation. Takes `session`
    because the sanctions leg reads the local sanctions index (`SanctionsRepository`);
    the CNPJ registry leg makes its own live HTTP call and needs no session."""
    return SupplierVerificationAdapter(
        cnpj_adapter=CnpjRegistryAdapter(),
        sanctions_adapter=SanctionsAdapter(SanctionsRepository(session)),
    )
