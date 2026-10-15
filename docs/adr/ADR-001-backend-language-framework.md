# ADR-001 — Backend Language & Framework

## Status
Accepted (database-hosting decision changed 2026-10-15 -- see that addendum; the language/
framework decision this ADR is actually about is unaffected)

## Context
JuriSense Gate needs a backend that is strong at: document/AI processing (contract extraction,
structured LLM output), async I/O for external verification calls (company registries, sanctions
lists), and fast iteration for a small team building toward a hackathon deadline (Legal Hack 2026,
judging 2026-11-05 to 2026-12-05) while also being viable as a long-term commercial product. The
repository audit (2026-09-27) found an existing, tested `Accounts` bounded context already built on
Python 3.13 + FastAPI (async SQLAlchemy 2.0 + asyncpg, Alembic, PyJWT, Argon2, Redis), with ~700
lines of passing tests and a documented security audit (`docs/auditorias/`).

## Decision
Keep **Python 3.13 + FastAPI** as the backend language/framework, async-first, with SQLAlchemy 2.0
+ asyncpg against PostgreSQL -- self-hosted as of the 2026-10-15 addendum below (originally the
external managed Neon instance). Reuse the `Accounts` context's architecture pattern (domain/
application/infrastructure/api layering) as the template for all new bounded contexts.

## Alternatives Considered
- **Node.js/TypeScript + NestJS**: single language across front/back, strong async I/O; weaker
  ecosystem for document parsing (PDF/DOCX), OCR, and ML tooling than Python.
- **Go**: excellent performance/concurrency, small footprint; weak/immature ecosystem for LLM
  orchestration, RAG, and document AI compared to Python; would require rewriting the already-built
  and audited Accounts context from scratch.
- **Django / Django Ninja**: batteries-included, but heavier synchronous-by-default ORM patterns and
  less natural fit for the async, event-driven processing this product needs (AI extraction,
  external verification calls, anchoring).

## Consequences
- The team keeps ~2100 lines of already-implemented, tested, and security-audited code
  (`backend/app/accounts/`) instead of discarding it.
- Python's AI/document ecosystem (LLM SDKs, `pypdf`/`unstructured`, `cel-python`/`json-logic`,
  OCR bindings) is directly available without a polyglot backend.
- The team must still port/rename domain-specific identifiers in `Accounts` (Portuguese, legal-role
  enums) as tracked in `docs/09-planning/pivot-migration.md` — this ADR does not resolve that; it
  only confirms the language/framework choice stands through the pivot.

## Addendum (2026-10-15) — database hosting changed from external Neon to self-hosted PostgreSQL

Decision (explicit instruction): PostgreSQL is now **self-hosted**, in both development
(`docker-compose.yml`'s `postgres` service, `pgvector/pgvector:pg17` image -- official, PostgreSQL-
licensed, no AGPL/distribution concern unlike MinIO's situation in `ADR-008`'s addendum) and
production (`docker-compose.prod.yml`, same image, credentials from `.env.production`). `app/core/
config.py`'s `_normalize_database_url` (libpq-style URL -> asyncpg, `sslmode` -> `ssl`, the Neon-
pooler-specific `prepared_statement_cache_size=0` heuristic) is unaffected -- it still runs, just
never matches the new default local URL's plain `postgresql+asyncpg://` shape with no `-pooler`
hostname, so it's a no-op against the new default rather than code that needs removing.

Rationale: same reasoning as `ADR-008`'s storage addendum -- avoid an external managed-service
dependency (billing, data-residency, another account to manage) when self-hosting is already the
model this project uses for its other infrastructure. `pgvector` (ADR-009) is enabled via a
`docker-entrypoint-initdb.d` init script (`postgres/init/001-enable-pgvector.sql`) rather than
Neon's own per-project toggle.

Status: Resolved (2026-10-15) / Decision: self-hosted PostgreSQL + pgvector, `pgvector/pgvector:
pg17`, dev and production / Verified live: all 21 Alembic migrations applied cleanly against a
fresh instance, full backend test suite (591 tests) green, a real register/login round trip
confirmed against it / Decision artifact: this addendum.

Not yet done as part of this addendum: production backup/restore strategy for the new self-hosted
instance (tracked separately, Plane `#167`-`#170`, previously scoped around Neon's own managed
backups -- now needs re-scoping to match self-hosting); `docker-compose.prod.yml` has not yet been
run against real production infrastructure, only validated as merged Compose config.
