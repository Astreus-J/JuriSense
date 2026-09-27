# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Repository State

JuriSense is an AI-powered Vendor, Contract & Compliance Operations Platform. Its first product is
**JuriSense Gate**: a B2B platform automating supplier and contract compliance review via AI, an
executable policy engine, approval workflows, an audit trail, and a blockchain evidence
verification layer. The product pivoted to this concept on 2026-09-27, discontinuing an earlier
legal-ERP concept for Brazilian law firms (archived at `docs/_legacy/`, not deleted). Git branch in
use: `develop`.

**Language rule (project-wide, from 2026-09-27 onward): everything is written in English** — code,
comments, docstrings, identifiers, database columns, API schemas, domain terminology, tests, logs,
error messages, ADRs, commit messages, branch names, PR descriptions, and future Plane
issues/labels/states. Portuguese exists only as explicit, supported customer-facing i18n content.
The reused `Accounts` code still has Portuguese identifiers (`Organizacao`, `Usuario`,
`organizacao_id`, etc.) — this is tracked migration debt, not an exception to the rule; see
`docs/09-planning/pivot-migration.md`. `docs/auditorias/` and everything under `docs/_legacy/`
predate this rule and are kept in their original language as historical record — do not translate
them retroactively.

## Project management (Plane)

`docs/` is the source of truth for architecture/product/business decisions; **Plane** (workspace
`astreus-develop`, project `JURI`) is the source of truth for work planning and execution — issues,
priorities, cycles, the Hackathon Cut. See `docs/07-engineering/project-management.md` for the
workflow and `project-management/plane/` for the configuration-as-code + `scripts/plane/bootstrap.py`
that applies it. When picking up implementation work in this repo, check Plane for the relevant
Ready issue first rather than inventing scope.

## Documentation

Full product, domain, architecture, business, and planning documentation lives in `docs/`, indexed
at [`docs/README.md`](docs/README.md). Start with `docs/00-project/overview.md` for the complete
picture. Key entry points:

- `docs/03-domain/domain-model.md` and `policy-engine.md` — the authoritative domain model and
  decision-aggregation algorithm (also formalized in `docs/adr/ADR-010-decision-aggregation-model.md`).
- `docs/01-product/functional-requirements.md` and `docs/03-domain/business-rules.md` — traceable
  requirement/rule IDs (`ORG-*`, `SUP-*`, `CON-*`, `POL-*`, `CMP-*`, `APR-*`, `DEC-*`, `EVD-*`,
  `AUD-*`, `AI-*`, `SEC-*`, `INT-*` / `BR-*`) — cite these in code comments, tests, and PRs when
  implementing a specific requirement.
- `docs/adr/` — 16 ADRs recording every major technical decision (backend/framework, architecture
  style, multi-tenancy/RBAC, policy engine language, AI provider abstraction, async/workflow model,
  blockchain anchoring, storage, RAG, decision aggregation, plus 6 formalized historical decisions
  from the Accounts build). Consult before proposing a new technology choice covered by an existing
  ADR; add a new ADR for any new significant decision.
- `docs/09-planning/roadmap.md`, `backlog.md`, and `implementation-plan.md` — the phased build plan
  and the concrete, ordered next-implementation-steps sequence.
- `docs/09-planning/pivot-migration.md` — exactly what in the existing codebase is reusable,
  adaptable (rename), or to be removed as part of the pivot.

## Repository Structure

- `frontend/` — Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 app. Currently contains the
  (pre-pivot) landing page; `src/lib/landing-data.ts` and `src/components/landing/` content need a
  full rewrite for the new product (tracked in `docs/09-planning/pivot-migration.md`), but the
  technical shell (App Router, Tailwind v4, component decomposition, multi-stage distroless
  Dockerfile) is reused as-is. Commands: `npm run dev` / `npm run build` / `npm run lint`.
- `backend/` — Python 3.13 + FastAPI API managed with uv. Layout: `app/main.py` (`create_app` +
  lifespan), `app/core/` (`config.py`, `db.py`, `redis.py`, `security.py`), `app/api/router.py`
  aggregates route modules under `/api` (docs at `/api/docs`). `app/accounts/` is the existing,
  security-audited Identity & Organizations context (JWT + refresh rotation, Argon2id, Redis
  lockout/token-store, invites, per-user RBAC grid, multi-tenancy by `organizacao_id`) — being
  adapted (not rewritten) to the new domain's role/module vocabulary per `ADR-003` and
  `pivot-migration.md`. The remaining 7 bounded contexts (Suppliers, Contracts & Documents, Policy &
  Compliance, Approvals & Decisions, Evidence & Audit, AI Services, Integrations) do not exist yet —
  see `docs/07-engineering/repository-structure.md` for the target layout and
  `docs/09-planning/implementation-plan.md` for build order. Tests: pytest + httpx
  `ASGITransport`. Commands: `uv sync`, `uv run uvicorn app.main:app --reload`, `uv run pytest`,
  `uv run ruff check .`. Multi-stage `Dockerfile` (uv builder → `python:3.13-slim` non-root runtime).
- `docker-compose.yml` — dev environment: frontend (3000) and backend (8000) built from each
  Dockerfile's `dev` stage with source mounted for hot reload, plus `redis:7-alpine` (6379) with
  healthcheck. **No local Postgres**: the database is the external managed PostgreSQL (Neon);
  `DATABASE_URL` lives in `backend/.env` (gitignored), loaded via `env_file`, normalized from
  libpq-style URLs to asyncpg by `app/core/config.py`. Per `ADR-006` and `ADR-008`, this file will
  gain a Celery worker service and a MinIO service for local object storage as those contexts are
  implemented — see `docs/07-engineering/development-workflow.md`. `docker compose up -d` runs
  everything currently defined.
- `docs/` — see "Documentation" above. `docs/_legacy/` holds the fully-archived pre-pivot product
  documentation (legal-ERP concept) — read `docs/_legacy/README.md` before assuming anything there
  still applies; it does not, except as historical/technical-debt context explicitly cited by the
  new documentation.

## Planned Architecture (big picture)

Modular monolith (`ADR-002`): one FastAPI deployment, 8 internal bounded contexts communicating only
through application-layer interfaces (never cross-context ORM access — see
`docs/04-architecture/components.md` for the explicit boundary rules). PostgreSQL (external, Neon) +
`pgvector` for retrieval (`ADR-009`), Redis + Celery for async processing with a DB-backed state
machine for approval workflows (`ADR-006`), S3-compatible object storage — R2 in production, MinIO
in dev (`ADR-008`), a multi-provider AI gateway (OpenAI + Anthropic, structured output only,
`ADR-005`), a YAML-authored policy DSL compiling to CEL/JSONLogic (`ADR-004`), and a
provider-agnostic blockchain `AnchoringProvider` abstraction (`ADR-007`) — no chain SDK is called
directly anywhere else in the codebase. Hosting stays VPS + Docker Compose with external DB, AI
APIs, object storage, and anchoring network (`docs/04-architecture/deployment.md`).

## Working in this repository

- Before implementing a feature, check whether it maps to an existing functional requirement
  (`docs/01-product/functional-requirements.md`) or backlog item (`docs/09-planning/backlog.md`) —
  cite the ID in the PR description and, where practical, in a code comment near the implementation.
- Before choosing a technology/pattern already covered by an ADR, read that ADR — don't re-litigate
  a decision documented as `Accepted` without new information; if an ADR is `Proposed` pending a
  spike, that spike is real backlog work, not something to skip past silently.
- Every sprint ends with a security audit (`ADR-016`) — see `docs/auditorias/` for the existing
  reports on the Accounts context as the established format/rigor to match for new contexts.
- Multi-tenancy is not optional anywhere: every tenant-owned table carries `organization_id`
  (`organizacao_id` in the not-yet-migrated Accounts tables), and every new repository method must
  be tested for cross-tenant access denial (`ADR-003`).
