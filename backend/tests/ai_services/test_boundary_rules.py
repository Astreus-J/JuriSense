"""AI-004 / `docs/04-architecture/components.md` rules 4-5: `AI Services` must never
write to a table owned by `Policy & Compliance` or `Approvals & Decisions`, and must
never call anything that creates a `ComplianceReview`, `RuleEvaluation`, or `Decision`.
Neither `Policy & Compliance` (`app/policies/`) nor `Approvals & Decisions`
(`app/approvals/`) exists as a working implementation yet (both are still empty
scaffolds) -- this test therefore holds vacuously today, exactly like the analogous
`tests/integrations/test_boundary_rules.py` note explains for its own still-unused
guard: it exists so a future PR introducing either context can't quietly wire `AI
Services` into it without a reviewer noticing, matching this codebase's stated
enforcement mechanism ("code review discipline... made automatic").

Mirrors `tests/suppliers/test_boundary_rules.py`'s AST-based approach exactly.
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
AI_SERVICES_DIR = APP_DIR / "ai_services"


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


def test_ai_services_never_imports_approvals_or_policies() -> None:
    """AI-004's concrete, regression-proof form: no file under `app/ai_services/` may
    import anything from `app.approvals.*` or `app.policies.*` -- the two contexts that
    own `Decision`/`ComplianceReview`/`RuleEvaluation`. `AI Services` only ever returns a
    structured DTO (`app.ai_services.domain.schema.ExtractionEnvelope`); the caller
    persists it into its own schema (`docs/04-architecture/components.md` rule 4)."""
    forbidden = {"app.approvals", "app.policies"}
    for path in _python_files(AI_SERVICES_DIR):
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports a Decision-owning context: {offending}"


def test_no_other_context_imports_ai_services_infrastructure_directly() -> None:
    """Symmetric to the Suppliers/Integrations pattern: nobody outside `app/ai_services/`
    may import its infrastructure (the concrete OpenRouter adapter, text extraction) --
    callers reach the AI Gateway only through
    `app.ai_services.application.extraction_service` / `app.ai_services.domain.ports`."""
    forbidden = {"app.ai_services.infrastructure"}
    for path in _python_files(APP_DIR):
        if AI_SERVICES_DIR in path.parents:
            continue
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports AI Services' infrastructure directly: {offending}"
