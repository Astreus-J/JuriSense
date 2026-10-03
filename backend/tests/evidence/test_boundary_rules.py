"""docs/04-architecture/components.md rule 3, applied to Evidence & Audit. It may read
Policy & Compliance, Contracts & Documents, Suppliers and Approvals data only through their
application-layer evidence ports and DTOs, never their infrastructure or ORM models. The API
layer may use Identity's permission dependency and user model, and nothing else of Identity.
Mirrors the AST-based pattern of tests/policies/test_boundary_rules.py exactly."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
EVIDENCE_DIR = APP_DIR / "evidence"


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


SANCTIONED_EVIDENCE_PORTS = {
    "app.policies.application.evidence_service",
    "app.policies.domain.evidence",
    "app.contracts.application.evidence_service",
    "app.contracts.domain.evidence",
    "app.suppliers.application.evidence_service",
    "app.suppliers.domain.evidence",
    "app.approvals.application.evidence_service",
    "app.approvals.domain.evidence",
}

SANCTIONED_IDENTITY_API_SURFACE = {
    "app.identity.api.deps",
    "app.identity.domain.constants",
    "app.identity.infrastructure.models",
}

OTHER_CONTEXTS = {"app.policies", "app.contracts", "app.suppliers", "app.approvals", "app.identity"}


def test_evidence_reads_other_contexts_only_through_their_evidence_ports() -> None:
    for path in _python_files(EVIDENCE_DIR):
        for module in _imported_modules(path):
            if not _starts_with_any(module, OTHER_CONTEXTS):
                continue
            allowed = _starts_with_any(module, SANCTIONED_EVIDENCE_PORTS) or _starts_with_any(
                module, SANCTIONED_IDENTITY_API_SURFACE
            )
            assert allowed, f"{path} imports an unsanctioned cross-context surface: {module}"


def test_evidence_never_imports_another_contexts_repositories_or_routes() -> None:
    forbidden_suffixes = (".infrastructure.repositories", ".api.routes")
    for path in _python_files(EVIDENCE_DIR):
        for module in _imported_modules(path):
            if not _starts_with_any(module, OTHER_CONTEXTS):
                continue
            if module.endswith(forbidden_suffixes) and not _starts_with_any(
                module, SANCTIONED_EVIDENCE_PORTS
            ):
                raise AssertionError(
                    f"{path} imports another context's repository/routes: {module}"
                )


def test_evidence_context_imports_only_the_sanctioned_identity_surface() -> None:
    """Only the API route imports Identity: its permission dependency, the Module enum and the
    User type. The assembly and service layers depend on no Identity internals at all."""
    for path in _python_files(EVIDENCE_DIR):
        touched = {m for m in _imported_modules(path) if _starts_with_any(m, {"app.identity"})}
        if "api" not in path.parts:
            assert not touched, f"{path} (non-API layer) imports Identity: {touched}"
