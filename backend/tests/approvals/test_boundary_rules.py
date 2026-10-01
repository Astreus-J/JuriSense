"""docs/04-architecture/components.md rule 3, extended to the new Approvals & Decisions
context (EPIC-6): it may read Policy & Compliance data only through that context's
sanctioned application-layer surface (`compliance_review_service.get_review_detail`, used
by `app.approvals.api.routes.list_requests` for the "does this review belong to my org"
ownership check) -- never by importing Policies' ORM/`infrastructure`/domain internals
directly. It must never touch Contracts & Documents or Suppliers at all. Mirrors
`tests/policies/test_boundary_rules.py`'s 3-test AST-based shape exactly."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
APPROVALS_DIR = APP_DIR / "approvals"


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


def test_approvals_never_imports_policies_contracts_or_suppliers_infrastructure_directly() -> None:
    forbidden = {
        "app.policies.infrastructure",
        "app.contracts.infrastructure",
        "app.suppliers.infrastructure",
    }
    for path in _python_files(APPROVALS_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, (
            f"{path} imports Policies'/Contracts'/Suppliers' infrastructure directly: "
            f"{offending}"
        )


def test_approvals_never_imports_policies_domain_or_contracts_or_suppliers_surfaces() -> None:
    """Approvals & Decisions must never touch Policies' SQLAlchemy model instances or
    domain vocabulary (`app.approvals.domain.constants.SeverityTier`'s own docstring
    explains why: Policies already depends on Approvals, so the reverse import would
    create a cross-context cycle) -- and must never touch Contracts/Suppliers at all,
    even their sanctioned evidence-port surfaces (Approvals has no legitimate reason to
    read either of those contexts directly)."""
    forbidden = {
        "app.policies.infrastructure.models",
        "app.policies.domain.constants",
        "app.policies.domain.rule_dsl",
        "app.policies.domain.context_schema",
        "app.contracts",
        "app.suppliers",
    }
    for path in _python_files(APPROVALS_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports an unsanctioned surface: {offending}"


def test_approvals_only_imports_the_sanctioned_policies_surface() -> None:
    """The only allowed Policies surface is `compliance_review_service.get_review_detail`
    (the ownership check `list_requests` reuses, per this epic's own instruction not to
    reinvent it) and `app.policies.domain.errors` (to translate
    `ComplianceReviewNotFoundError` to HTTP 404) -- nothing else of Policies' may be
    imported anywhere in this package."""
    allowed = {
        "app.policies.application.compliance_review_service",
        "app.policies.domain.errors",
    }
    watched_prefixes = {"app.policies"}
    for path in _python_files(APPROVALS_DIR):
        touched = {m for m in _imported_modules(path) if _starts_with_any(m, watched_prefixes)}
        offending = {m for m in touched if not _starts_with_any(m, allowed)}
        assert not offending, f"{path} imports an unsanctioned Policies surface: {offending}"
