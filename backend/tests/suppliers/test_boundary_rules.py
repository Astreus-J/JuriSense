"""STORY-2.5 / docs/04-architecture/components.md: `Suppliers` may depend on
`SupplierVerificationPort` (a Protocol, `app.integrations.domain.ports`) and call into
`app.integrations.application.*` (an application-layer function call), but must never
import `app.integrations.infrastructure` directly — the concrete CNPJ/sanctions adapters
are Integrations' private implementation detail.

This is the "small new test that specifically imports and checks app/suppliers/ files"
called for in EPIC-2's brief: `tests/integrations/test_boundary_rules.py`'s existing
`test_no_other_context_imports_integrations_infrastructure_directly` already walks every
context under `app/`, Suppliers included, so that check was already covering this rule
before this file existed. This file exists only to make the Suppliers-specific case
explicit and independently regression-proof, not to duplicate general enforcement.
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
SUPPLIERS_DIR = APP_DIR / "suppliers"


def _python_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*.py") if "__pycache__" not in p.parts]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _starts_with_any(module: str, prefixes: set[str]) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def test_suppliers_never_imports_integrations_infrastructure_directly() -> None:
    """`app/suppliers/` must reach the CNPJ/sanctions adapters only through
    `app.integrations.application.supplier_verification_service.get_supplier_verification_port`
    — never by importing `app.integrations.infrastructure` (the concrete adapters) itself.
    """
    forbidden = {"app.integrations.infrastructure"}
    for path in _python_files(SUPPLIERS_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports Integrations' infrastructure directly: {offending}"


def test_suppliers_only_imports_integrations_domain_and_application() -> None:
    """The allowed surface from Suppliers into Integrations is exactly: the domain
    `ports` module (the `SupplierVerificationPort` Protocol/DTOs) and the application
    layer (the factory function) — never `app.integrations.domain.constants` internals
    like `SanctionsList` (Integrations' own private vocabulary for its adapters) nor,
    per the test above, `app.integrations.infrastructure`.
    """
    allowed = {"app.integrations.domain.ports", "app.integrations.application"}
    for path in _python_files(SUPPLIERS_DIR):
        integrations_imports = {
            m for m in _imported_modules(path) if _starts_with_any(m, {"app.integrations"})
        }
        offending = {m for m in integrations_imports if not _starts_with_any(m, allowed)}
        assert not offending, f"{path} imports an unexpected Integrations surface: {offending}"
