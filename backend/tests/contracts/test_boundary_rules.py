"""`docs/04-architecture/components.md` boundary rules for `Contracts & Documents`:

- Rule 2: must not import or query `Suppliers`' ORM models directly -- `Contract.supplier_id`
  is a plain foreign-key value, never a cross-context join.
- Rule 4 (the `Contracts & Documents` side of AI-004): reaches the AI Gateway only through
  `app.ai_services.application`/`app.ai_services.domain.ports`, never
  `app.ai_services.infrastructure` directly -- mirrors
  `tests/suppliers/test_boundary_rules.py`'s Integrations check exactly.
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
CONTRACTS_DIR = APP_DIR / "contracts"


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


def test_contracts_never_imports_suppliers_orm_directly() -> None:
    """Rule 2: `Contract.supplier_id` is a plain FK value -- Contracts must never import
    `app.suppliers.infrastructure`/`app.suppliers.domain` to query or join Supplier data."""
    forbidden = {"app.suppliers.infrastructure", "app.suppliers.domain"}
    for path in _python_files(CONTRACTS_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, (
            f"{path} imports Suppliers' domain/infrastructure directly: {offending}"
        )


def test_contracts_never_imports_ai_services_infrastructure_directly() -> None:
    forbidden = {"app.ai_services.infrastructure"}
    for path in _python_files(CONTRACTS_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports AI Services' infrastructure directly: {offending}"


def test_contracts_only_imports_ai_services_domain_and_application() -> None:
    allowed = {
        "app.ai_services.domain.ports",
        "app.ai_services.domain.schema",
        "app.ai_services.domain.errors",
        "app.ai_services.application",
    }
    for path in _python_files(CONTRACTS_DIR):
        ai_imports = {
            m for m in _imported_modules(path) if _starts_with_any(m, {"app.ai_services"})
        }
        offending = {m for m in ai_imports if not _starts_with_any(m, allowed)}
        assert not offending, f"{path} imports an unexpected AI Services surface: {offending}"
