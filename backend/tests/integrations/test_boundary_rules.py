"""STORY-1.4.1 / docs/04-architecture/components.md rule 8: "Integrations must never write
directly to business-domain tables." The symmetric half of that boundary — nobody else
should import Integrations' ORM models to write to them either, and Integrations itself
should never import another context's domain/infrastructure layer directly — is checked
here.

Lightweight AST-based check, not a dedicated import-linter dependency: consistent with
`docs/07-engineering/coding-standards.md`'s stated enforcement mechanism ("code review
discipline, not a network boundary or import linter"), just made automatic so a future PR
can't quietly regress it before a reviewer notices.
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
INTEGRATIONS_DIR = APP_DIR / "integrations"

# Every other bounded context (docs/04-architecture/components.md §1); `core` is the shared
# kernel every context is allowed to depend on, so it's excluded.
OTHER_CONTEXTS = [
    "identity",
    "suppliers",
    "contracts",
    "policies",
    "approvals",
    "evidence",
    "ai_services",
]


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


def test_no_other_context_imports_integrations_infrastructure_directly() -> None:
    """Nobody outside `app/integrations/` may import its ORM models/repositories — a future
    caller must go through an application-layer port instead (rule 8's symmetric case;
    nothing calls into Integrations yet, so this currently vacuously holds and simply can't
    regress silently).
    """
    forbidden = {"app.integrations.infrastructure"}
    for path in _python_files(APP_DIR):
        if INTEGRATIONS_DIR in path.parents:
            continue
        offending = {m for m in _imported_modules(path) if _starts_with_any(m, forbidden)}
        assert not offending, f"{path} imports Integrations' infrastructure directly: {offending}"


def test_integrations_never_imports_another_contexts_domain_or_infrastructure() -> None:
    """`Integrations` must never write directly to business-domain tables (rule 8's primary
    case) — enforced here at the import level: it may depend on `app.core` and its own
    layers, never on another context's `domain`/`infrastructure` package to query or write
    that context's data.

    Two narrow, deliberate exceptions, not a loophole: `require_permission` (STORY-1.1.2,
    `app.identity.api.deps`) is *designed* to be called by every bounded context's routes,
    and its own public usage contract requires the caller to (1) reference `Module`/`Role`
    from `app.identity.domain.constants` -- shared RBAC vocabulary, not Identity's private
    business data -- to say which module/action it's gating, and (2) type-annotate the
    dependency's injected result as `app.identity.infrastructure.models.User`, purely as a
    type hint for the value FastAPI already injects -- never to import a repository and
    query/write Identity's tables directly, which is what this rule actually guards against.
    Any future context adopting `require_permission` (Suppliers, Contracts, ...) needs the
    exact same two imports, so this exception is structural, not Integrations-specific.
    """
    forbidden = {
        prefix
        for context in OTHER_CONTEXTS
        for prefix in (f"app.{context}.domain", f"app.{context}.infrastructure")
    }
    allowed_exceptions = {"app.identity.domain.constants", "app.identity.infrastructure.models"}
    for path in _python_files(INTEGRATIONS_DIR):
        offending = {
            m
            for m in _imported_modules(path)
            if _starts_with_any(m, forbidden) and not _starts_with_any(m, allowed_exceptions)
        }
        assert not offending, f"{path} imports another context's domain/infrastructure: {offending}"
