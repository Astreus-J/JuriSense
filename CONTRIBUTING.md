# Contributing to JuriSense

This guide is entirely in English, because so is everything else in this project — see the
English-only rule below.

## English-only engineering policy

JuriSense uses English as its canonical engineering and product-development language. This
includes: source code, variable/function/class names, database fields and tables, API routes,
domain terminology, comments, docstrings, test descriptions, fixtures, seed data, logs, exceptions,
error messages, documentation, diagrams, ADRs, commit messages, branch names, pull request titles
and descriptions, and every Plane issue/module/cycle/label/state.

Portuguese may be used only for customer-facing localized content, through a proper i18n mechanism,
once explicitly supported. It is never mixed directly into internal implementation. New code
containing unnecessary Portuguese internal naming or comments fails review — for example:

```python
# Not allowed
def criar_fornecedor():
    # verifica se fornecedor existe
    ...

# Expected
def create_supplier():
    # Check whether the supplier already exists.
    ...
```

Existing Portuguese identifiers in the reused `Accounts` code (`Organizacao`, `Usuario`,
`organizacao_id`, etc.) are tracked migration debt, not an exception — see
`docs/09-planning/pivot-migration.md` and Plane's `EPIC-0` (Foundation).

## Development workflow

1. Pick a **Ready** issue from Plane (see `docs/07-engineering/project-management.md`), preferably
   one in the current cycle. If nothing relevant is Ready, check the Definition of Ready before
   pulling a Backlog item forward.
2. Create a branch: `feature/<slug>`, `fix/<slug>`, `refactor/<slug>`, `docs/<slug>`,
   `chore/<slug>`, or `spike/<slug>` — lowercase, hyphenated, English.
3. Move the Plane issue to **In Progress**.
4. Implement against the issue's acceptance criteria. Cross-reference the relevant
   `docs/03-domain/`, `docs/04-architecture/`, or `docs/adr/` document — don't duplicate that
   explanation in the issue or the PR, link to it.
5. Write tests per `docs/07-engineering/testing-strategy.md`. Run `uv run ruff check .` and
   `uv run pytest` (backend) or `npm run lint` and `npm run build` (frontend) before opening a PR.
6. Open a PR, move the issue to **In Review**. Use
   [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.
7. On merge, move the issue to **Done**. If the change affects documentation, update it in the same
   PR — don't let `docs/` drift from what shipped.

## Plane workflow

Full detail in `docs/07-engineering/project-management.md`: issue hierarchy, states, priorities,
label taxonomy, cycles, Definition of Ready/Done. Every issue should link back to the repository
documentation it implements, not restate it.

## Pull request requirements

Include: **Summary**, **Related Issue** (Plane link), **Changes**, **Testing**, **Security Impact**,
**Architecture Impact** (if any), and a checklist confirming lint/tests/docs are updated. PR titles
start with a verb, in English, matching the linked issue's intent.

## Branch naming

See `docs/07-engineering/project-management.md`. In short: `feature/`, `fix/`, `refactor/`, `docs/`,
`chore/`, `spike/` prefixes, lowercase-hyphenated, English.

## Commit style

Conventional Commits, English only: `feat(suppliers): add supplier onboarding`,
`fix(auth): enforce tenant isolation`, `test(contracts): add extraction regression cases`.

## Testing

See `docs/07-engineering/testing-strategy.md`. At minimum: unit tests for new logic, an integration
test for new API behavior, and — for anything touching multi-tenancy — a cross-tenant-access denial
test (mandatory per `docs/adr/ADR-003-multi-tenancy-rbac.md` and `ADR-016`).

## Documentation

If a change affects product behavior, architecture, or a business rule, update the corresponding
file under `docs/` in the same PR. `docs/` is the source of truth for *what the system is and why*;
Plane is the source of truth for *what work is happening*. Keep them pointing at each other, not
duplicating each other.

## Code quality

Follow `docs/07-engineering/coding-standards.md`: the layered domain/application/infrastructure/api
structure per bounded context, the cross-context boundary rules in
`docs/04-architecture/components.md`, and the English-only rule above.
