# Deployment Architecture

How JuriSense Gate actually runs, consistent with the project's established hosting philosophy:
**a single VPS running Docker Compose, with only the AI provider APIs and the anchoring network as
external dependencies.** This document states what's unchanged from the pre-pivot hosting decision
and what the pivot adds — see `containers.md` for the container-level detail this builds on, and
`docs/07-engineering/deployment-runbook.md` for the actual `docker-compose.prod.yml` this diagram
describes, plus the step-by-step commands to stand it up on a VPS.

**Update (2026-10-15):** PostgreSQL and object storage are no longer external dependencies.
`ADR-001`'s and `ADR-008`'s addenda moved both to self-hosted containers on the same VPS (`pgvector/
pgvector:pg17`, and MinIO built from source) — the sections below still describe the original
pre-pivot/pivot framing (Neon, Cloudflare R2) as historical context for *why* object storage and
Postgres have the shape they have (durability, versioning, pgvector), but the actual hosting
location described in §2/§3 is superseded by that update. The diagram below reflects the current,
self-hosted state.

## 1. Diagram

```mermaid
flowchart TB
    subgraph internet["Internet"]
        USER["Tenant users / public verifiers"]
    end

    CF["Cloudflare<br/>CDN + WAF, TLS termination"]

    subgraph vps["Single VPS — Docker Compose"]
        NGINX["Nginx<br/>reverse proxy"]
        FE["frontend container<br/>Next.js, :3000"]
        API["backend container<br/>FastAPI, :8000"]
        WORK["worker container(s)<br/>Celery worker"]
        BEAT["beat container<br/>Celery beat"]
        REDIS[("redis container<br/>:6379")]
        PG[("postgres container<br/>pgvector/pgvector:pg17, :5432")]
        MINIO[("minio container<br/>built from source, :9000")]
    end

    AIAPI["OpenAI / Anthropic<br/>external APIs"]
    ANCHOR["AnchoringProvider network<br/>external (ADR-007, TBD)"]
    SMTP["SMTP provider<br/>external"]

    USER --> CF --> NGINX
    NGINX --> FE
    NGINX --> API
    API --> REDIS
    API --> PG
    API --> MINIO
    API --> AIAPI
    WORK --> REDIS
    WORK --> PG
    WORK --> MINIO
    WORK --> AIAPI
    WORK --> ANCHOR
    WORK --> SMTP
    BEAT --> REDIS
```

## 2. Unchanged from the pre-pivot hosting decision

These were decided before the pivot to JuriSense Gate and remain exactly as they were:

- **Single VPS, Docker Compose** as the deployment unit — no Kubernetes, no multi-node orchestration.
  Justified by the same reasoning as ADR-002 (modular monolith): small team, tight timeline, no
  production traffic yet to justify the operational overhead of a distributed platform.
- **PostgreSQL** — unchanged by the pivot itself (already the pre-pivot choice before the domain
  changed from legal-ERP to compliance automation), though *where* it runs changed later: see the
  2026-10-15 update at the top of this document (self-hosted, not external Neon, as of `ADR-001`'s
  addendum). `DATABASE_URL` lives in `backend/.env` (gitignored), loaded via `env_file`, normalized
  libpq→asyncpg by `app/core/config.py::_normalize_database_url` regardless of where the instance
  runs. Required to have the `pgvector` extension enabled (ADR-009) — enabled via a
  `docker-entrypoint-initdb.d` init script on the self-hosted instance.
- **External AI provider APIs** (OpenAI/Anthropic) reached over HTTPS — the "VPS + external DB +
  external AI APIs" philosophy stated in `docs/00-project/overview.md`'s Technology strategy section
  and in ADR-008's own framing ("consistent with the... hosting philosophy already established for
  this project") predates the pivot and is exactly what this deployment keeps.
- **Redis on the VPS itself** (not external) — `redis:7-alpine` container, healthchecked, with a
  named volume (`redis_data`). Unchanged.
- **Cloudflare fronting the VPS** as CDN/WAF, terminating TLS at the edge before traffic reaches the
  VPS's Nginx reverse proxy. Unchanged in principle (the current `docker-compose.yml` doesn't yet
  include an `nginx` service — that's a pre-existing gap in the dev compose file, not a pivot-specific
  one; the target production topology has always assumed it, per the plan captured in
  `docs/00-project/overview.md`'s "Planned Architecture" framing carried from `CLAUDE.md`).

## 3. Newly added by the pivot

- **Celery worker + Celery beat containers** (ADR-006) — new services in `docker-compose.yml`, built
  from the same `backend` image with a different entrypoint (`containers.md` §3). Needed because the
  pre-pivot product had no async task processing requirement of this shape; JuriSense Gate's AI
  extraction, registry lookups, and blockchain anchoring all require it.
- **Object storage** (ADR-008): originally planned as s3mock (dev-only) + Cloudflare R2 (an
  *external* production dependency) — superseded 2026-10-15 by self-hosted **MinIO**, built from
  source, running as a container on the same VPS in both dev and production (see the update at the
  top of this document). Still supersedes the pre-pivot plan of storing documents on the VPS
  filesystem under `/dados/empresas/{organizacao_id}/` with encrypted off-VPS backups (still
  reflected in the current `documents_data` Docker volume) — object storage gets versioning and
  durability "for free" instead of hand-rolled backup scripting (ADR-008's own stated rationale).
  The `documents_data` volume is not deleted immediately; it is phased out as new uploads move to
  MinIO (`data-architecture.md` §4.2, `containers.md` §5).
- **`AnchoringProvider` network egress** (ADR-007): a new category of *outbound-only* external
  dependency — the VPS's Celery workers make outbound HTTPS/RPC calls to submit hashes and poll
  proofs (`blockchain-architecture.md` §2). No inbound connection from the anchoring network is ever
  required, which keeps this addition low-risk from a network-exposure standpoint: it is one more
  outbound allowlist entry on the VPS firewall, not a new listening port.
- **pgvector extension** (ADR-009) — not a new service, but a new requirement on the Postgres
  instance, enabled via a `docker-entrypoint-initdb.d` init script now that it's self-hosted.

## 4. What did not change and was never going to

- No move to Cloud Run/Cloud SQL/Pub/Sub or any GCP-native service — those describe the *old*
  architecture docs (`docs/_legacy/IMPLEMENTACAO_ARQUITETURA/`), explicitly superseded by the VPS
  decision (see `CLAUDE.md`'s "Known Documentation Inconsistencies"). Nothing in the pivot to
  JuriSense Gate reopens that question.
- No move away from FastAPI/Next.js — ADR-001 reaffirms Python/FastAPI specifically because of the
  already-built, already-audited `Accounts` context; the pivot changes the *domain*, not the
  *stack*.

## 5. Environment variables added to `backend/.env` / `docker-compose.yml` for the pivot

Building on the existing `Settings` class (`app/core/config.py`), the following new settings groups
are required (exact field names are an implementation detail, listed here for completeness of the
deployment picture, not as a frozen contract):

| Group | Purpose | Dev default | Prod requirement |
|---|---|---|---|
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Point Celery at Redis | Reuses `REDIS_URL` | Same pattern, required |
| `OBJECT_STORAGE_ENDPOINT` / `_ACCESS_KEY` / `_SECRET_KEY` / `_BUCKET_DOCUMENTS` / `_BUCKET_EVIDENCE` | S3-compatible client config (ADR-008) | Points at the `minio` container | Points at the production `minio` container (self-hosted, not R2 -- 2026-10-15 update), required, no dev default |
| `AI_PROVIDER_OPENAI_API_KEY` / `AI_PROVIDER_ANTHROPIC_API_KEY` | AI Gateway credentials (ADR-005) | Required even in dev (no mock provider planned for realistic testing) | Required |
| `ANCHORING_PROVIDER` / `ANCHORING_PROVIDER_CREDENTIALS` | Selects and authenticates the `AnchoringProvider` adapter (ADR-007) | Dev/test can point at a testnet | Points at whichever network the Phase 8 spike selects |

Every one of these follows the existing pattern in `app/core/config.py`: added as a `Settings` field
with a safe dev default where one exists, and — for anything security-sensitive (API keys, storage
credentials, anchoring credentials) — validated as required and non-placeholder when
`environment == "production"`, mirroring `_exige_segredo_em_producao`'s existing check for
`JWT_SECRET_KEY` (`security-architecture.md` §4).
