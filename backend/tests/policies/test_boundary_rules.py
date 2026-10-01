"""docs/04-architecture/components.md rule 3: `Policy & Compliance` may read `Suppliers`
and `Contracts & Documents` data only through their read-only application-layer evidence
ports (`get_normalized_profile`/`get_normalized_terms`/`get_supplier_id_for_contract_version`),
never by importing those contexts' ORM models/`infrastructure` directly. Mirrors
`tests/suppliers/test_boundary_rules.py` / `tests/contracts/test_boundary_rules.py`'s
existing AST-based pattern exactly.

EPIC-6 extends the sanctioned-surface discipline to the new, one-way Policy & Compliance
-> Approvals & Decisions dependency (`compliance_review_service.trigger_review`'s own
call site): Policies may call exactly `approval_service.create_approval_requests_for_review`/
`decision_service.create_decision_for_review` (both application-layer, the first
write-side -- not read-only "evidence port" -- cross-context calls in this codebase) and,
in the API layer, `NoApprovalWorkflowConfiguredError` to translate that error to HTTP --
never Approvals' ORM/infrastructure directly."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
POLICIES_DIR = APP_DIR / "policies"


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


def test_policies_never_imports_suppliers_or_contracts_infrastructure_directly() -> None:
    forbidden = {
        "app.suppliers.infrastructure",
        "app.contracts.infrastructure",
        "app.approvals.infrastructure",
    }
    for path in _python_files(POLICIES_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, (
            f"{path} imports Suppliers'/Contracts' infrastructure directly: {offending}"
        )


def test_policies_never_imports_suppliers_or_contracts_domain_orm_or_repositories() -> None:
    """Rule 3 specifically forbids Policy & Compliance from touching those contexts'
    SQLAlchemy model instances -- so even `app.suppliers.infrastructure.models`/
    `app.contracts.infrastructure.repositories` (not just the package root) must never
    appear. The one exception is the DTO/evidence modules (`domain.evidence`), which are
    exactly what the port is supposed to return."""
    forbidden_domain = {
        "app.suppliers.domain.tax_id",
        "app.suppliers.domain.constants",
        "app.contracts.domain.constants",
        "app.contracts.domain.extracted_data",
        "app.approvals.domain.constants",
    }
    for path in _python_files(POLICIES_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden_domain)}
        assert not offending, (
            f"{path} imports an unexpected Suppliers/Contracts surface: {offending}"
        )


def test_policies_only_imports_the_sanctioned_evidence_port_surface() -> None:
    """The allowed surface from Policies into Suppliers/Contracts is exactly the two
    evidence-port application modules and their DTOs -- `app.suppliers.application.
    evidence_service`/`app.suppliers.domain.evidence` and `app.contracts.application.
    evidence_service`/`app.contracts.domain.evidence`."""
    allowed = {
        "app.suppliers.application.evidence_service",
        "app.suppliers.domain.evidence",
        "app.contracts.application.evidence_service",
        "app.contracts.domain.evidence",
        # EPIC-6: the first write-side (not read-only "evidence port") cross-context
        # calls in this codebase -- see compliance_review_service.trigger_review's own
        # docstring note -- plus the one approvals-domain error the API layer translates
        # to HTTP (policies/api/routes.py's trigger_review handler).
        "app.approvals.application.approval_service",
        "app.approvals.application.decision_service",
        "app.approvals.domain.errors",
    }
    watched_prefixes = {"app.suppliers", "app.contracts", "app.approvals"}
    for path in _python_files(POLICIES_DIR):
        touched = {
            m for m in _imported_modules(path) if _starts_with_any(m, watched_prefixes)
        }
        offending = {m for m in touched if not _starts_with_any(m, allowed)}
        assert not offending, (
            f"{path} imports an unsanctioned Suppliers/Contracts surface: {offending}"
        )
