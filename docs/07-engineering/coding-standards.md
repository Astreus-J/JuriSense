# Coding Standards

These are the concrete standards every contributor (human or agent) follows when writing code for
JuriSense Gate. They apply to `backend/`, `frontend/`, infrastructure config, and this documentation
tree itself. Where this document and a linter disagree, fix the linter config via a PR, don't
silently diverge in code.

## The English-only rule (read this first)

**As of this documentation pass (2026-09-27), the entire project is 100% English.** This is a
project-wide rule, not a style preference, and it applies to absolutely everything written from now
on:

- Code: variable, function, class, and module names.
- Comments and docstrings.
- Database identifiers: table names, column names, enum values, index names, constraint names.
- API schemas: field names, enum values, error messages returned to API consumers.
- Domain terminology: bounded context names, entity names, event names, error class names.
- Tests: test names, fixture names, assertion messages.
- Logs and error messages, including ones surfaced to end users via the API (the frontend i18n layer
  translates them for display — see the exception below).
- ADRs, commit messages, branch names, PR titles/descriptions.
- Future Plane issues, labels, and workflow states.

**The only exception** is explicit customer-facing i18n content in the frontend (UI copy strings
that go through a translation layer to be displayed to Brazilian end users in pt-BR). Everything
upstream of that translation layer — the API contract, error codes, domain model — stays English.

**The existing `Accounts` code is not compliant with this rule and that is known.** It was built
before this pivot with Portuguese identifiers throughout: `Organizacao`, `Usuario`, `Perfil`,
`organizacao_id`, `senha_hash`, `criado_em`, error classes like `EmailJaCadastradoError`, and
Portuguese docstrings/comments. **Do not "fix" this opportunistically as a side effect of unrelated
work** — it is tracked as deliberate migration debt with its own inventory and sequencing in
`docs/09-planning/pivot-migration.md` (a separate document covers the full inventory of what needs
renaming and in what order, including the Alembic migration strategy for renaming live columns).
Two rules bound this in the meantime:

1. **New code is English from day one.** Every one of the other seven bounded contexts
   (Suppliers, Contracts & Documents, Policy & Compliance, Approvals & Decisions, Evidence & Audit,
   AI Services, Integrations) is written entirely in English, with no exceptions, even though they
   sit next to the Portuguese `Accounts` context.
2. **Don't extend the Portuguese surface.** Adding a new field, endpoint, or table to the existing
   `Accounts` context uses English names for the new addition, even if neighboring fields in the
   same table are still Portuguese. Do not add `data_nascimento` next to `criado_em`; add
   `date_of_birth`. This keeps the migration debt from growing while the tracked rename work is
   scheduled.

## Naming conventions

- **Python**: `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_SNAKE`
  for constants and enum members. Bounded-context packages are lowercase, singular-vs-plural matched
  to the domain noun (e.g. `app/suppliers/`, `app/contracts/`, `app/policies/`, `app/approvals/`,
  `app/evidence/`, `app/ai_services/`, `app/integrations/`), mirroring `app/accounts/`.
- **TypeScript/React**: `camelCase` for variables/functions, `PascalCase` for components and types,
  `SCREAMING_SNAKE_CASE` for module-level constants. Component files are `PascalCase.tsx` matching
  the exported component name, consistent with `frontend/src/components/landing/`.
- **Database**: `snake_case` table and column names, always singular domain nouns for entities that
  map 1:1 to an aggregate root's table name in plural (e.g. `suppliers`, `contract_versions`,
  `policy_versions`, `rule_evaluations`) — see `docs/07-engineering/database-standards.md` for the
  full naming table.
- **API**: JSON field names are `snake_case` to match the Python/Pydantic models directly with no
  translation layer, avoiding the `camelCase`-JSON/`snake_case`-Python impedance mismatch bugs.
- **Domain error classes**: `<Reason>Error`, e.g. `SupplierNotFoundError`, `PolicyVersionImmutableError`,
  `CrossTenantAccessError` — English equivalents of the existing pattern
  (`EmailJaCadastradoError`, `UsuarioInativoError`) in `app/accounts/domain/errors.py`.
- **Domain events**: `<context>.<entity>.<verb_past_tense>` dotted strings, matching the existing
  catalog style in `docs/03-domain/domain-model.md` (`supplier.created`, `compliance.review_completed`,
  `decision.overridden`).
- **Git branches**: `<type>/<short-description>`, e.g. `feat/suppliers-sanctions-check`,
  `fix/policy-version-race`. **Types**: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`,
  matching the existing commit-message convention seen in `git log` (`feat(backend): ...`,
  `docs: ...`, `chore(docker): ...`).

## Bounded-context layering (domain / application / infrastructure / api)

Every bounded context — the existing `app/accounts/` and all seven new ones — follows the same
four-layer structure. This is restated briefly here for the coding rule it implies; the full
architectural rationale and diagrams live in `docs/04-architecture/components.md`.

```
app/<context>/
  domain/           # Entities, value objects, domain errors, pure business rules. No I/O, no
                     # framework imports (no FastAPI, no SQLAlchemy). Importable and testable
                     # in isolation.
  application/      # Use cases / services that orchestrate domain objects and ports. Depends on
                     # domain/ and on abstract ports (interfaces), never on a concrete ORM model
                     # or a concrete FastAPI request/response type.
  infrastructure/   # Concrete adapters: SQLAlchemy models and repositories, Redis-backed stores,
                     # email senders, external API clients. Implements the ports application/
                     # defines. This is the only layer allowed to import SQLAlchemy, redis-py,
                     # httpx clients to third parties, etc.
  api/              # FastAPI routers, Pydantic request/response schemas, dependency wiring
                     # (`Depends`). Translates HTTP concerns (status codes, headers, auth) to and
                     # from application-layer calls. Contains no business logic.
```

**The explicit cross-context boundary rules** (full detail and the enforcement mechanism in
`docs/04-architecture/components.md`; restated briefly because they are load-bearing for every PR
review):

1. **No cross-context ORM access.** Context A never imports Context B's SQLAlchemy models or issues
   a query against Context B's tables. If Context A needs data owned by Context B, it calls Context
   B's application-layer interface (a port), in-process.
2. **AI Services never decides a compliance outcome.** It produces structured, schema-validated
   extraction output with provenance; only `Policy & Compliance` interprets that output against
   rules (ADR-005, ADR-010).
3. **Integrations never writes directly to business-domain tables.** External system connectors
   emit/consume events and call application-layer commands, never their own ad hoc writes into
   `suppliers`, `contracts`, etc. (`docs/03-domain/domain-model.md`, `Integration` entity).
4. This is enforced today by **code review discipline**, not a network boundary or import linter —
   the modular monolith (ADR-002) trades that enforcement cost for avoiding premature microservices
   overhead. A reviewer rejecting a cross-context ORM import is not being pedantic; it is the
   mechanism that keeps the monolith modular instead of a ball of mud.

## Type-hinting requirements (Python)

- **All new Python code is fully type-hinted.** Function signatures (parameters and return type),
  class attributes (via `Mapped[...]` for ORM models, plain annotations elsewhere), and module-level
  constants all carry explicit types. `Any` is a last resort, justified with a comment when used
  (see `AccessPayload = Annotated[dict[str, Any], Depends(get_access_payload)]` in
  `app/accounts/api/deps.py` — a JWT payload's shape genuinely varies by claim, hence `Any`; this is
  the acceptable pattern, not an excuse to type everything as `Any`).
- Use modern built-in generics (`list[str]`, `dict[str, int]`, `X | None`) — Python 3.13 syntax, not
  `typing.List`/`typing.Optional`, consistent with the `UP` (pyupgrade) ruff rule already enabled.
- Public application-layer functions and repository methods have complete type signatures; private
  helper functions may omit return type only when it is `None` and obvious from context.
- Pydantic models (`api/schemas.py`) are the single source of truth for request/response shapes —
  do not hand-write a parallel `TypedDict` or dataclass for the same data.
- `mypy`/`pyright` are not currently wired into CI (see `docs/07-engineering/ci-cd.md`'s typecheck
  stage) but ruff's `UP` and `F` rule sets catch a meaningful subset of type issues in the
  meantime; adding a dedicated type checker to CI is tracked as a near-term follow-up, not a
  currently-enforced gate.

## Error handling conventions

Follow the existing, audited pattern in `app/accounts/domain/errors.py` and
`app/accounts/api/routes.py`, in English for all new contexts:

1. **Domain exceptions are plain Python exceptions, not HTTP-aware.** Every bounded context defines
   a `<Context>Error` base class and specific subclasses (e.g. `SupplierNotFoundError`,
   `SanctionsCheckFailedError`, `PolicyVersionImmutableError`). Domain and application layers raise
   these and only these — never `fastapi.HTTPException`.
2. **The API layer translates domain exceptions to HTTP responses**, one `except` clause per
   meaningful case, exactly as `routes.py` does today: catch the specific domain error, raise
   `HTTPException` with the right status code and a message safe to return to a client. Never let a
   raw domain exception or an unrelated internal exception escape to the client as a 500 with
   internal detail.
3. **Status code conventions**: `400` malformed input the schema layer didn't already reject,
   `401` unauthenticated, `403` authenticated but not authorized (wrong role/module/action),
   `404` not found *or* found-but-cross-tenant (never reveal cross-tenant existence — see
   `docs/07-engineering/security.md`), `409` conflict on a caller-controlled unique constraint,
   `422` validation failure with a structured detail, `429` rate-limited, `402` plan-limit exceeded
   (matching the existing `LimiteUsuariosAtingidoError` pattern).
4. **Never leak enumeration through error messages or status-code differences** — this is a codified
   lesson from `docs/auditorias/sprint-01.md` (MED-002) and `sprint-02.md`: registration,
   password-reset, and any future "does X exist" endpoint return an identical response whether or
   not the resource exists, and cross-tenant lookups return `404`, never `403` (a `403` would
   confirm the resource exists in another tenant).
5. Every raised domain exception that reaches the API boundary is a deliberate, named case — no bare
   `except Exception` swallowing errors into a generic response. Truly unexpected exceptions
   propagate and are caught by a single global handler that logs with full context and returns a
   generic `500` with no internal detail (see `docs/07-engineering/observability.md` for what gets
   logged).

## Docstring policy

Docstrings are **minimal and reserved for non-obvious WHY**, not restating WHAT the code already
says. This mirrors this project's own engineering philosophy of favoring self-documenting,
well-named code over narration (visible in the existing codebase's sparse-but-purposeful comments,
e.g. the `MED-002: evita enumeração` comment in `routes.py`, kept in English going forward as
`# MED-002: avoids enumeration`). Concretely:

- **Do not** write a docstring that just repeats the function name in sentence form
  (`"""Gets the user by id."""` on `get_user_by_id` adds nothing — omit it).
- **Do** write a docstring or inline comment when the *why* isn't derivable from the code itself:
  a security rationale (why a response is intentionally generic), a business-rule citation (`BR-CMP-002`,
  an ADR number), a non-obvious ordering requirement, or a workaround for an external system's
  quirk (e.g. the existing `_normalizar_database_url` comment explaining why `sslmode` must become
  `ssl` for asyncpg — that is exactly the kind of comment to keep writing, just in English).
- Module-level and class-level docstrings are used sparingly, for bounded-context entry points
  (`app/<context>/__init__.py` or the top of `domain/`) to state the context's one-sentence purpose
  and point to `docs/03-domain/domain-model.md`, not to duplicate it.
- Public API endpoints may carry a one-line docstring where it changes what shows up in
  `/api/docs` (FastAPI renders a route's docstring as its OpenAPI description) — this is a
  documentation-generation concern, not narration, and is worth doing precisely because it is
  externally visible.

## Lint / format tooling

- **ruff** is the single tool for both linting and formatting the backend (`uv run ruff check .`,
  `uv run ruff format .`), already configured in `backend/pyproject.toml` with `line-length = 100`,
  `target-version = "py313"`, and rule sets `E`, `W`, `F`, `I` (isort-equivalent), `B` (bugbear),
  `UP` (pyupgrade), `SIM` (simplify). New bounded contexts inherit this configuration automatically
  (it applies repo-wide under `backend/`); do not add a per-context ruff config.
- Every new rule-set addition to `[tool.ruff.lint].select` is a deliberate PR with a one-line reason
  in the PR description, not silently expanded.
- `alembic/versions` is excluded from linting (`extend-exclude`) because autogenerated migration
  files should not be hand-edited to satisfy style rules.
- **ESLint** (`npm run lint`, `eslint-config-next`) is the equivalent for `frontend/`; keep the
  Next.js default rule set unless a specific rule is actively causing friction, in which case
  disable it explicitly with a comment explaining why, not silently in a broad ignore file.
- CI runs both linters as a gate before tests (`docs/07-engineering/ci-cd.md`) — a failing lint
  blocks merge, it is not advisory.

## Security-relevant coding conventions (cross-reference)

Tenant-isolation, input validation, and secret-handling conventions that affect how code is written
day to day are specified once, completely, in `docs/07-engineering/security.md` — this document
does not repeat them to avoid drift between the two.
