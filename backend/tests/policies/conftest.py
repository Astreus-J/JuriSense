"""Re-exports fixtures/helpers from Suppliers'/Contracts' test suites so Policies tests
(#61's simulation flow needs a real Supplier + ContractVersion) don't have to duplicate
their hermetic HTTP-mocking setup -- same chaining pattern
`tests/contracts/conftest.py` already uses for `register_org_and_login`."""

from tests.contracts.conftest import (  # noqa: F401
    HIGH_CONFIDENCE_ENVELOPE,
    create_supplier,
    mock_openrouter,
    pdf_bytes_with_text,
)
from tests.suppliers.conftest import (  # noqa: F401
    ACTIVE_CNPJ_RESPONSE,
    mock_cnpj_registry,
    seed_sanctions_index,
)
