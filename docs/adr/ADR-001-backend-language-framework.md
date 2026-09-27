# ADR-001 — Backend Language & Framework

## Status
Accepted

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
+ asyncpg against the existing external PostgreSQL (Neon). Reuse the `Accounts` context's
architecture pattern (domain/application/infrastructure/api layering) as the template for all new
bounded contexts.

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
