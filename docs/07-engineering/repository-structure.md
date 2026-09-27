# Repository Structure

This is the target repository layout once all 8 bounded contexts exist, extending the pattern the
`Accounts` context already established. It is a target, not a rewrite mandate — contexts are added
incrementally per the roadmap (`docs/09-planning/roadmap.md`); this document exists so every new
context is scaffolded consistently from day one instead of drifting.

## Top level

```
JuriSense/
├── backend/                  # Python 3.13 + FastAPI modular monolith (see below)
├── frontend/                 # Next.js 16 + React 19 + TypeScript app (see below)
├── JuriSense_frontend/       # legacy Vite/React prototype — reference only, not built/deployed
├── docker-compose.yml        # dev stack: frontend, backend, redis, minio (ADR-008)
├── docs/                     # all product/architecture/engineering documentation (see below)
└── README.md
```

## Backend (`backend/app/`)

Eight bounded contexts as sibling packages, each following the `domain/application/infrastructure/api`
layering documented in `docs/07-engineering/coding-standards.md`. `accounts/` is the existing,
already-implemented context (kept as-is structurally; its Portuguese identifiers are tracked
migration debt per `docs/09-planning/pivot-migration.md`, not a structural difference). The other
seven are new and English-named from creation.

```
backend/
├── alembic/                          # migrations, shared across all contexts (one DB, ADR-002)
│   ├── versions/
│   └── env.py
├── alembic.ini
├── app/
│   ├── main.py                       # create_app() + lifespan — unchanged entry point
│   ├── api/
│   │   ├── router.py                 # aggregates every context's router under /api
│   │   └── routes/
│   │       └── health.py
│   ├── core/                         # cross-cutting, framework-level concerns only —
│   │   │                             # never business logic for a specific bounded context
│   │   ├── config.py                 # pydantic-settings, one Settings object for the app
│   │   ├── db.py                     # engine/session factory, declarative Base
│   │   ├── redis.py                  # Redis client factory
│   │   ├── security.py               # JWT encode/decode primitives (context-agnostic)
│   │   ├── storage.py                # S3-compatible object storage client (ADR-008; new)
│   │   ├── ai_gateway.py             # thin re-export of ai_services' public interface for
│   │   │                             # contexts that only need to call it (kept minimal —
│   │   │                             # the real gateway lives in app/ai_services/)
│   │   └── observability.py          # structured logging/tracing setup (see observability.md)
│   │
│   ├── accounts/                     # Identity & Organizations (existing, reused — ADR-001/013)
│   │   ├── domain/                   # entities, errors, rules (Portuguese identifiers — debt)
│   │   ├── application/              # auth_service, user_service, invite_service, password_service
│   │   ├── infrastructure/           # models.py, repositories.py, email.py, token_store.py, lockout.py
│   │   └── api/                      # routes.py, users.py, schemas.py, deps.py
│   │
│   ├── suppliers/                    # Suppliers (new — English from day one)
│   │   ├── domain/                   # Supplier, SupplierProfile, SupplierCheck entities + errors
│   │   ├── application/              # supplier_service, sanctions_check_service
│   │   ├── infrastructure/           # models.py, repositories.py, external source adapters
│   │   │                             # (CEIS/CNEP/CEPIM clients — Brazil jurisdiction pack)
│   │   └── api/                      # POST /suppliers, GET /suppliers/{id}, etc.
│   │
│   ├── contracts/                    # Contracts & Documents (new)
│   │   ├── domain/                   # Contract, ContractVersion, Clause, Document entities
│   │   ├── application/              # ingestion_service, extraction_orchestration_service
│   │   ├── infrastructure/           # models.py, repositories.py, storage adapter usage
│   │   └── api/                      # POST /contracts, contract upload endpoints
│   │
│   ├── policies/                     # Policy & Compliance (new)
│   │   ├── domain/                   # Policy, PolicyVersion, Rule, ComplianceReview, RuleEvaluation,
│   │   │                             # Risk entities; the CEL/JSONLogic rule compiler (ADR-004)
│   │   ├── application/              # policy_authoring_service, compliance_review_service,
│   │   │                             # evaluation_context_normalizer (ADR-010 aggregation logic)
│   │   ├── infrastructure/           # models.py, repositories.py
│   │   └── api/                      # POST /compliance/check, policy CRUD endpoints
│   │
│   ├── approvals/                    # Approvals & Decisions (new)
│   │   ├── domain/                   # ApprovalWorkflow, ApprovalRequest, Decision entities
│   │   ├── application/              # approval_routing_service, decision_service (override logic)
│   │   ├── infrastructure/           # models.py, repositories.py
│   │   └── api/                      # GET /decisions/{id}, approval action endpoints
│   │
│   ├── evidence/                     # Evidence & Audit (new)
│   │   ├── domain/                   # Evidence, EvidencePackage, AuditEvent, BlockchainAnchor
│   │   ├── application/              # evidence_packaging_service, anchoring_service (uses the
│   │   │                             # AnchoringProvider port, ADR-007), audit_log_service
│   │   ├── infrastructure/           # models.py, repositories.py, anchoring provider adapters
│   │   └── api/                      # GET /evidence/{id}, GET /verify/{hash} (public)
│   │
│   ├── ai_services/                  # AI Services (new)
│   │   ├── domain/                   # extraction schemas, provenance value objects
│   │   ├── application/              # ai_gateway_service — extract()/classify()/summarize()
│   │   │                             # with provider fallback (ADR-005); never decides outcomes
│   │   ├── infrastructure/           # openai_adapter.py, anthropic_adapter.py, rag_retriever.py
│   │   │                             # (pgvector-backed, ADR-009)
│   │   └── api/                      # internal-only in v1 (no public HTTP surface yet)
│   │
│   └── integrations/                 # Integrations (new)
│       ├── domain/                   # Integration entity, provider-specific event contracts
│       ├── application/              # integration_service (never writes to other contexts'
│       │                             # tables directly — calls their application layer)
│       ├── infrastructure/           # per-provider adapters (DocuSign, Slack, future ERP)
│       └── api/                      # webhook receivers, integration config endpoints
│
├── tests/
│   ├── conftest.py                   # shared fixtures: db_engine, client, sent_emails, fake_redis
│   ├── accounts/                     # existing tests (Portuguese test data — matches existing code)
│   ├── suppliers/
│   ├── contracts/
│   ├── policies/                     # includes fixture-based Policy Engine tests (testing-strategy.md)
│   ├── approvals/
│   ├── evidence/                     # includes AnchoringProvider mock/testnet tests
│   ├── ai_services/                  # includes recorded-fixture contract tests (no live API calls)
│   └── integrations/
│
├── pyproject.toml
├── .env.example
└── Dockerfile
```

**Rule for adding a ninth package**: don't. Eight bounded contexts is a deliberate, ADR-backed scope
(ADR-002). A new capability first asks "does this belong inside an existing context's
`application/`?" before a new top-level package is proposed, and that proposal goes through a new
ADR, not an ad hoc `mkdir`.

## Frontend (`frontend/src/`)

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router pages
│   │   ├── (marketing)/              # landing page route group — existing
│   │   ├── (app)/                    # authenticated product routes (new, per bounded context UI):
│   │   │   ├── suppliers/
│   │   │   ├── contracts/
│   │   │   ├── policies/
│   │   │   ├── approvals/
│   │   │   ├── decisions/
│   │   │   └── evidence/
│   │   └── verify/[hash]/            # public, unauthenticated verification page (docs/06-blockchain/verification.md)
│   ├── components/
│   │   ├── landing/                  # existing marketing sections
│   │   └── app/                      # product UI components, organized per bounded context
│   ├── lib/
│   │   ├── landing-data.ts           # existing
│   │   └── api-client.ts             # typed fetch wrapper against /api/v1 (api-standards.md)
│   └── styles/
├── public/
├── next.config.ts                    # output: "standalone"
├── package.json
└── Dockerfile
```

## Documentation (`docs/`)

```
docs/
├── 00-project/          # overview.md — single entry point for the whole project
├── 01-product/          # personas, functional requirements, use cases, future vision
├── 02-business/         # market sizing, competitive landscape, business model, pricing
├── 03-domain/           # domain-model.md, business-rules.md, policy-engine.md, audit.md
├── 04-architecture/     # components.md (bounded-context boundary rules), architecture-overview.md
├── 05-ai/               # ai-strategy.md, structured-extraction.md, rag.md, evaluation.md,
│                        # observability.md, guardrails.md
├── 06-blockchain/       # blockchain-purpose.md, privacy.md, anchoring-providers.md, verification.md
├── 07-engineering/      # this directory — engineering standards and practices
│   ├── technology-stack.md
│   ├── coding-standards.md
│   ├── repository-structure.md
│   ├── api-standards.md
│   ├── database-standards.md
│   ├── testing-strategy.md
│   ├── observability.md
│   ├── security.md
│   ├── ci-cd.md
│   └── development-workflow.md
├── 08-hackathon/        # hackathon-specific strategy and submission material
├── 09-planning/         # roadmap.md, backlog.md, pivot-migration.md
├── adr/                 # ADR-001 through ADR-016 (and future ADRs), numbered sequentially
├── auditorias/          # end-of-sprint security audit reports (ADR-016), one per sprint
└── _legacy/             # superseded pre-pivot docs, kept for historical traceability only
```

**Rule**: a new engineering standard document goes in `07-engineering/`; a new domain concept goes
in `03-domain/`; a new architectural decision is an ADR in `adr/`, not a freeform doc. This keeps
the "where does this belong" question answerable by directory name alone.
