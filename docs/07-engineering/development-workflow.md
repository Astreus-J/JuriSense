# Development Workflow

Local developer experience and the sprint-based process this project already runs, extended for the
full 8-bounded-context product.

## Docker Compose dev stack

The existing `docker-compose.yml` runs `frontend` (3000), `backend` (8000), and `redis` (6379, with
a healthcheck), with source mounted for hot reload and named volumes shadowing `node_modules`/`.next`/
`.venv` so container-installed dependencies don't fight the host's. `docker compose up -d` brings up
everything needed to develop against. Two changes extend this for the full product:

- **Add a `minio` service (ADR-008)**: local S3-compatible object storage for document/evidence
  uploads, replacing the pre-pivot `documents_data` filesystem volume as the storage backend
  developers actually write against (the compose file's current `documents_data:/dados/empresas`
  volume reflects the superseded pre-ADR-008 filesystem-storage decision and is retired once MinIO is
  wired in — this doc states the target, the compose file change itself is implementation work, not a
  documentation-only edit). Concretely:

  ```yaml
  minio:
    image: minio/minio:latest
    container_name: jurisense-minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # web console
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-jurisense}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-jurisense-dev-only}
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 3s
      retries: 10
  ```

  The backend service gains `STORAGE_ENDPOINT_URL`/`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`/
  `STORAGE_BUCKET` env vars pointing at `minio:9000` in dev and at the real R2 endpoint/credentials
  in production (`backend/.env`, gitignored, same pattern as `DATABASE_URL` today) — one storage
  abstraction in code, environment-driven backend swap, per ADR-008.
- **No local Postgres, unchanged**: the database remains the external managed PostgreSQL (Neon),
  loaded via `backend/.env`'s `DATABASE_URL` — this decision (`26e3bf9 chore(docker): remove Postgres
  local`) stands for the full product; adding a local Postgres service would reintroduce the
  drift/parity problems that decision removed.

## Environment variable validation on startup

- `Settings` (`app/core/config.py`, pydantic-settings) is the single source of truth for
  configuration; every new required setting is added there with a typed field, not read ad hoc via
  `os.environ.get()` elsewhere in the codebase.
- The existing `_exige_segredo_em_producao` validator pattern — refusing to boot in `environment ==
  "production"` with an insecure default — is the model for every new secret-shaped setting: AI
  provider API keys, object storage credentials, and the eventual `AnchoringProvider` credentials all
  get an equivalent "don't start in production without a real value" guard, not just a type
  annotation.
- A missing *required* setting (one with no sensible default, e.g. `DATABASE_URL` in a non-dev
  environment) fails at application startup with a clear pydantic-settings validation error, not at
  first use deep in a request handler — this is already how `Settings()` behaves by construction
  (a missing required field raises at `Settings()` instantiation, i.e. at import time via
  `get_settings()`), and new settings should preserve that property by only defaulting fields that are
  genuinely safe to default (like `cors_origins`), not ones that are unsafe if silently defaulted
  (like a production secret).

## Seed data / fixtures for local development

A fresh `docker compose up -d` plus an empty Neon dev branch is not enough to manually exercise the
product end to end — a seed script populates realistic sample data:

- A `backend/scripts/seed_dev_data.py` (or an Alembic data migration gated behind
  `environment == "development"`) creates: one sample `Organization` on a mid-tier plan, two or three
  `User`s across different roles (`admin`, `legal`, `compliance`, `procurement`) so role-based UI/API
  behavior is manually testable without registering fresh accounts every time, a handful of
  `Supplier`s in different statuses (`prospect`, `under_review`, `approved`, `blocked` — including at
  least one with a seeded sanctions hit, to exercise the `BLOCK` path end to end), a couple of
  `Contract`s with `ContractVersion`s covering different risk profiles (a low-risk auto-approve
  candidate, a high-value contract that should trigger `REVIEW`/director approval, and one with an
  unlimited-liability clause to exercise `LEGAL-008`), and a sample `PolicyVersion` with the example
  rules already documented in `docs/03-domain/policy-engine.md` (`LGPD-001`, `LEGAL-008`, `FIN-003`,
  `FIN-004`, `SANC-001`) pre-published so `POST /compliance/check` is exercisable immediately after
  seeding.
- Seed data is idempotent (safe to run repeatedly against the same dev database without duplicating
  rows — upsert by a natural key, not blind insert) and is never run against a shared staging/
  production database by accident (gated on `environment == "development"`, matching the existing
  guard pattern in `config.py`).
- Seed data uses realistic-but-clearly-fake values (e.g. `contato@empresa-exemplo.com.br`, a
  well-known test CNPJ format) — never real company/personal data, even for a "just for local dev"
  script, consistent with LGPD-first handling of anything resembling personal data throughout the
  product.

## Pre-commit hooks

- `ruff check --fix` and `ruff format` run as a pre-commit hook (via the `pre-commit` framework or a
  simple git hook script) against staged Python files, so lint/format issues are caught before they
  reach CI, not just before merge.
- An equivalent ESLint check (and Prettier, if/when adopted) runs against staged frontend files.
- A lightweight secret-pattern check (the same class of check as CI's secret scanning, run locally
  and fast) catches an accidental credential commit at the earliest possible point — before it is
  ever pushed, let alone merged.
- Pre-commit hooks are fast (seconds, not minutes) by design — they run lint/format/secret-pattern
  checks only, never the full test suite; that stays in CI (`docs/07-engineering/ci-cd.md`) where a
  few minutes of latency is acceptable and local-loop speed is not sacrificed.
- Hooks are never bypassed with `--no-verify` as routine practice — if a hook is wrong or too strict,
  fix the hook configuration in a PR, don't habitually skip it.

## Sprint-based workflow and the security audit gate

- Work proceeds in sprints (visible in the existing commit history: "Sprint 2 do Accounts", "TODO
  1.8 — paridade do sistema de usuários", etc.), each scoped to a specific bounded-context slice of
  functionality per the roadmap phases (`docs/09-planning/roadmap.md`).
- **Every sprint ends with a mandatory security audit before the next sprint starts** (ADR-016) —
  this is a hard gate, not a best-effort review: `security-review` + `insecure-defaults` skills plus
  the manual checklist (always including the cross-tenant-access test) produce a report following the
  `docs/auditorias/sprint-01.md`/`sprint-02.md` template (scope, method, findings by severity with
  location/impact/fix, verifications-with-no-findings, a routing table). Critical/high findings block
  starting the next sprint's work; lower-severity findings get an explicit, documented disposition
  (fixed now, scheduled for a named future sprint, or accepted as a reasoned risk) — never silently
  dropped.
- Roughly 3 capacity-points per sprint are budgeted for this audit work (ADR-016) — it is planned
  capacity, not slack absorbed opportunistically, which is what makes the gate sustainable sprint over
  sprint instead of skipped under deadline pressure.
- New-context sprints (Suppliers, Contracts & Documents, Policy & Compliance, Approvals & Decisions,
  Evidence & Audit, AI Services, Integrations) follow the exact same audit ritual as the already-completed
  `Accounts` sprints — there is no "the audit is optional for a new context because it's new";
  if anything a brand-new context's first audit deserves *more* scrutiny than an already-hardened one.

## Local commands quick reference

- Backend: `uv sync`, `uv run uvicorn app.main:app --reload`, `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format .`, `uv run alembic upgrade head`.
- Frontend: `npm run dev`, `npm run build`, `npm run lint`.
- Full stack: `docker compose up -d` (frontend, backend, redis, and — once added — minio).
