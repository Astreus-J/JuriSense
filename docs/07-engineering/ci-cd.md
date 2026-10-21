# CI/CD

**Recommended platform: GitHub Actions** — consistent with this project's existing GitHub-centric
tooling (the `gh` CLI is already the standard way this project interacts with GitHub for issues/PRs),
avoiding a second CI vendor/account to manage for a small team.

## Pipeline stages

The pipeline is a sequence of gates, each one cheaper and faster than the next, so a change fails as
early (and as cheaply) as possible — a lint error is caught in seconds, not after a 10-minute
integration-test run.

```
1. Lint            →  2. Format check   →  3. Typecheck (backend)
        ↓
4. Unit tests       →  5. Integration tests
        ↓
6. Security checks (dependency + secret scanning)
        ↓
7. Build (frontend build, backend package check)
        ↓
8. Container build (Docker images)
        ↓
9. Migration check (alembic upgrade head against a throwaway DB)
        ↓
10. AI eval suite (scheduled/gated — not every commit)
        ↓
11. Deployment
```

### 1. Lint
`uv run ruff check backend/` and `npm run lint --prefix frontend/`. Fails fast, no dependency install
beyond the tool itself is needed for the Python side (ruff has no project deps to resolve).

### 2. Format check
`uv run ruff format --check backend/` — verifies code is already formatted, does not auto-fix in CI
(auto-fixing belongs in local dev / pre-commit, `docs/07-engineering/development-workflow.md`).
Equivalent Prettier/ESLint `--fix`-free check for `frontend/` if/when a formatter is added there.

### 3. Typecheck (backend)
Not currently wired (`docs/07-engineering/coding-standards.md` notes this as a near-term follow-up,
not a currently-enforced gate) — when added, `mypy` or `pyright` runs here, before tests, since a
type error is cheaper to catch than a failing test. `frontend/`'s `tsc --noEmit` (implicit in
`next build`, step 7) is the equivalent already-available check on the TypeScript side.

### 4. Unit tests
`uv run pytest backend/tests/ -m "not integration"` (or an equivalent marker split) — the
domain/application-layer tests with no I/O, from `docs/07-engineering/testing-strategy.md`. Runs on
every PR, every push.

### 5. Integration tests
`uv run pytest backend/tests/` — the full httpx `ASGITransport` suite against in-memory SQLite/
fakeredis, matching the existing `backend/tests/conftest.py` setup. No external services needed, so
this stays fast and runs on every PR.

### 6. Security checks
- Dependency scanning: `uv lock --check` plus a vulnerability scan (`pip-audit` or Dependabot alerts)
  against `backend/pyproject.toml`/`uv.lock` and `frontend/package.json`/lockfile.
- Secret scanning: gitleaks (or GitHub's native secret scanning, if enabled on the repo) against the
  diff, catching an accidentally-committed credential before merge — this is the CI-side counterpart
  to the manual `grep` for secrets already performed during sprint audits
  (`docs/auditorias/sprint-02.md`).
- A critical/high finding here fails the pipeline outright — it is not advisory.

### 7. Build
`npm run build --prefix frontend/` (`next build`, which also runs the TypeScript compiler) and a
backend "does it import cleanly / does the package build" check (`uv build` or equivalent) — catches
a broken import or a frontend build-time error before it reaches container build, which is slower.

### 8. Container build
`docker build` for both `frontend/Dockerfile` and `backend/Dockerfile` (the existing multi-stage
builds — node:24-alpine → distroless Node 24 non-root for frontend; uv builder →
`python:3.13-slim` non-root runtime for backend, per `CLAUDE.md`). Verifies the production image
actually builds, not just that `npm run build`/local dev works — catches Dockerfile drift.

### 9. Migration check
`uv run alembic upgrade head` against a fresh, throwaway Postgres instance (a GitHub Actions Postgres
service container), starting from an empty database — catches a migration that only works against a
developer's already-drifted local schema, or one with a syntax/dependency-ordering error. Runs on
every PR that touches `backend/alembic/` or `backend/app/**/infrastructure/models.py`.

### 10. AI eval suite
Runs the extraction-accuracy and guardrail evaluation described in
`docs/07-engineering/testing-strategy.md`/`docs/05-ai/evaluation.md`. **Deliberately not run on every
commit** — it costs real API spend and takes meaningfully longer than the rest of the pipeline.
Triggers:
- **Scheduled**: nightly, against the current `develop` branch, to catch drift (a provider silently
  changing model behavior, a fixture going stale) even without a relevant code change.
- **Gated**: required (blocking) specifically on PRs that touch prompts, extraction schemas, the AI
  Gateway's provider selection/fallback logic, or the RAG retrieval pipeline — everything else skips
  it.

### 11. Deployment
Deploys to the single VPS (`docker compose -f docker-compose.prod.yml up -d --build` against the
production compose file, or an equivalent SSH-based deploy step — see
`docs/07-engineering/deployment-runbook.md` for the actual commands, required secrets, and
troubleshooting) after every gate above passes on `develop` (or the project's designated release
branch) — no manual step required for a normal deploy, but deployment to production is not automatic
on every green PR merge unless/until the team decides that level of continuous deployment is
appropriate; until then, treat step 11 as a manually-triggered GitHub Actions workflow_dispatch gated
on all prior steps having passed.

## What blocks a merge vs. what blocks a deploy

- **Blocks merge (PR-level, required checks)**: lint, format check, unit tests, integration tests,
  security checks, build, migration check (when relevant files changed).
- **Blocks deploy but not merge**: the AI eval suite when it runs as a scheduled/nightly check rather
  than a PR-gated one — a regression found overnight is a fast-follow fix, not a reason to have
  blocked yesterday's unrelated PRs.
- **Never auto-merges around a failure**: no `--no-verify`-equivalent bypass of these gates exists for
  normal development; an admin override of a required check is an explicit, logged, rare action, not
  a routine escape hatch.

## Relationship to the sprint security audit

CI security checks (dependency/secret scanning, step 6) are continuous and automated; the end-of-sprint
security audit (ADR-016, `docs/07-engineering/security.md`) is periodic and manual/skill-assisted,
covering business-logic issues (cross-tenant access, privilege escalation, policy-engine bypass) that
static CI scanning does not catch. The two are complementary, not redundant — CI catches what
automation can catch every time; the sprint audit catches what requires judgment, on a fixed cadence
that the roadmap already budgets capacity for (ADR-016: "roughly 3 capacity-points per sprint").
