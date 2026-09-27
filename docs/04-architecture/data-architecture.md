# Data Architecture

Data ownership, multi-tenancy enforcement, migration strategy, and storage architecture. This
document is the source of truth for "which table belongs to which context" — `components.md`'s
boundary rules assume the ownership mapping below.

## 1. One physical database, logically partitioned by context

Per ADR-002 and ADR-009, all 8 contexts share **one PostgreSQL database** (external, Neon-managed —
`docker-compose.yml` deliberately runs no local Postgres). There is no schema-per-context or
database-per-context split; ownership is enforced by **code discipline** (only a context's own
`infrastructure/repositories.py` may construct queries against its own tables — `components.md` §3)
and by naming convention (table names are prefixed implicitly by which context's `infrastructure/`
module declares them, e.g. `app/suppliers/infrastructure/models.py` declares `suppliers`,
`supplier_profiles`, `supplier_checks` and nothing else).

## 2. Ownership map (all entities from `docs/03-domain/domain-model.md`)

| Bounded context | Owned tables (English names — see §6 on the pending Portuguese→English rename) | Domain entities |
|---|---|---|
| **Identity & Organizations** | `organizations`, `memberships`, `users`, `roles` (+ existing `tokens_recuperacao`→`password_reset_tokens`, `convites`→`invites`, `acessos`→`access_log`, `permissoes_modulo`→`module_permissions`) | `Organization`, `Membership`, `User`, `Role` |
| **Suppliers** | `suppliers`, `supplier_profiles`, `supplier_checks` | `Supplier`, `SupplierProfile`, `SupplierCheck` |
| **Contracts & Documents** | `documents`, `contracts`, `contract_versions`, `clauses` | `Document`, `Contract`, `ContractVersion`, `Clause` |
| **Policy & Compliance** | `policies`, `policy_versions`, `rules`, `compliance_reviews`, `rule_evaluations`, `risks` | `Policy`, `PolicyVersion`, `Rule`, `ComplianceReview`, `RuleEvaluation`, `Risk` |
| **Approvals & Decisions** | `approval_workflows`, `approval_requests`, `decisions` | `ApprovalWorkflow`, `ApprovalRequest`, `Decision` |
| **Evidence & Audit** | `evidence`, `evidence_packages`, `audit_events`, `blockchain_anchors` | `Evidence`, `EvidencePackage`, `AuditEvent`, `BlockchainAnchor` |
| **AI Services** | `ai_executions` (operational provenance log — model/provider/prompt version/cost/latency per call; **not** one of the 24 core domain entities, but required to back the Decision Passport's "AI executions (model/prompt version)" field per `docs/00-project/overview.md`) | none from the core domain model |
| **Integrations** | `integrations`, `integration_events` (inbound webhook inbox: raw payload + processing status, for replay/debugging) | `Integration` |

Cross-cutting, owned by `app/core` (shared kernel, not a bounded context): `outbox_events` (the
transactional-outbox table described in `components.md` §4) is written to by every context but its
schema/dispatcher logic lives in `app/core`, not inside any single context's `infrastructure/`
package — each context's rows in it are just data, distinguishable by an `origin_context` column.

## 3. Multi-tenancy enforcement (ADR-003)

**Every tenant-owned table carries an `organization_id` column**, either directly or by one hop
through a clearly-owning parent (documented per table below). There is no row-level security (RLS)
in v1 — isolation is enforced entirely at the **repository layer**: every `infrastructure/
repositories.py` method that reads or writes tenant data takes the caller's `organization_id`
(obtained from the authenticated `Membership` via `app/core`'s `get_current_membership()` dependency,
per `components.md` rule 10) and includes it in the `WHERE` clause or the inserted row — never as an
optional filter, always as a mandatory parameter with no "fetch without a tenant filter" code path
exposed to callers outside `app/core`'s internal bootstrapping.

| Table (owning context) | `organization_id` | How |
|---|---|---|
| `organizations` | — (it *is* the tenant root) | N/A |
| `memberships`, `users`* | Direct on `memberships`; `users` has none (a `User` may belong to multiple orgs) | `memberships.organization_id` |
| `suppliers`, `contracts`, `policies`, `integrations` | Direct | Column on the table |
| `supplier_profiles`, `supplier_checks` | Via `Supplier.organization_id` | One-hop join enforced in the repository, never left to the caller |
| `documents`, `contract_versions`, `clauses` | Via `Contract`/`Document` → `organization_id` | One or two hops, same rule |
| `policy_versions`, `rules` | Via `Policy.organization_id` | One-hop |
| `compliance_reviews`, `rule_evaluations`, `risks` | Via `Contract`/`ComplianceReview` chain | Multi-hop, still enforced at the repository, never via a raw unscoped query |
| `approval_workflows` | Direct | Column on the table |
| `approval_requests`, `decisions` | Via `ComplianceReview` chain | Multi-hop |
| `evidence`, `evidence_packages` | Via `Decision` chain | Multi-hop |
| `blockchain_anchors` | Via `EvidencePackage` chain | Multi-hop |
| `audit_events` | Direct, **nullable** | Nullable specifically for system-level events with no single tenant (per `docs/03-domain/domain-model.md`) |
| `ai_executions` | Direct (denormalized onto the log row for cheap filtering, even though it's also derivable via the triggering document/supplier) | Column on the table |

**Mandatory cross-tenant-access test** (ADR-003, ADR-016): every new repository method that reads a
row by non-tenant-scoped primary key (e.g. `get_contract_by_id(contract_id)`) must have an explicit
test asserting that a caller from a different `organization_id` gets a not-found/forbidden result,
not the row. This is a required item in every sprint's security audit, not an optional nice-to-have.

**Deferred hardening**: Postgres Row-Level Security is a documented v1.x item
(`docs/09-planning/backlog.md`), not a hackathon blocker — it would add defense-in-depth against a
repository-layer bug, but is not required for the current threat model given repository-layer
enforcement is total (no raw SQL access paths exist outside `infrastructure/`).

## 4. Storage architecture

Two storage tiers, per ADR-008 and ADR-009:

### 4.1 Relational + vector — PostgreSQL + pgvector

- All 24 domain entities' relational data lives in Postgres tables as listed in §2.
- `pgvector` (ADR-009) backs retrieval for: matching contract clauses against a policy playbook,
  searching prior compliance decisions for precedent, and (future) retrieving regulatory text. No
  standalone vector database in v1 — deferred until real query-latency/index-size data shows
  `pgvector` becoming a bottleneck.
- Embedding tables are owned by the context whose source data they embed, not by `AI Services` (AI
  Services computes the embedding vector via its gateway, but the owning context persists it):
  - `contract_clause_embeddings` (Contracts & Documents) — one row per `Clause`, `vector` column +
    `clause_id` FK.
  - `policy_rule_embeddings` / `decision_precedent_embeddings` (Policy & Compliance) — semantic
    search over rule text and past `ComplianceReview` rationale for precedent lookup.
- Hybrid retrieval combines `pgvector` similarity search with Postgres full-text search (`tsvector`)
  and metadata filters (`organization_id`, document type, `policy_version_id`) — see
  `docs/05-ai/rag.md` for the retrieval strategy itself; this section only states where the data
  lives and who owns it.

### 4.2 Object storage — documents and evidence (ADR-008)

- **Cloudflare R2** in production, **MinIO** in local dev (`containers.md` §5), both accessed through
  a single shared storage abstraction in `app/core/storage.py` — used directly by `Contracts &
  Documents` (uploaded documents) and `Evidence & Audit` (evidence package artifacts), per
  `components.md` rule 11. `Integrations` has no role here.
- **Key layout**: `{bucket}/{organization_id}/{context}/{entity_id}/{version_or_filename}` —
  e.g. `jurisense-docs-prod/3f2a.../contracts/9c1b.../v1/original.pdf`,
  `jurisense-evidence-prod/3f2a.../evidence-packages/7e4d.../package.json`. The `organization_id`
  prefix makes tenant-scoped bucket policies/audits straightforward even though the bucket itself is
  shared.
- **Versioning**: bucket versioning is enabled so a `ContractVersion`'s original file is retrievable
  forever even after re-analysis (domain-model invariant: "a `Document` is itself an immutable
  version; re-upload creates a new `Document`" — object storage versioning is a second,
  storage-layer guarantee behind that application-layer invariant, not a substitute for it).
- **What is never stored here**: no raw personal data or contract text is ever written on-chain
  (that's `blockchain-architecture.md`'s concern) — object storage holds the actual files; only
  **hashes** of what's in object storage get anchored.

### 4.3 Redis — cache and ephemeral state, not source of truth

Redis (`containers.md`) holds: the Celery broker/result backend queue state, the refresh-token
revocation blocklist (ADR-011), and a cache of the permission grid per `(user_id, organization_id)`
(ADR-012) with a short TTL and explicit invalidation on `membership.revoked`/`role.permissions_updated`
events. Nothing in Redis is the durable record of anything — a Redis flush must never lose domain
data, only force a cache repopulation and force already-issued refresh tokens to be re-validated
against the (now-empty) blocklist, which is a safe fail-open-to-re-auth degradation, not a security
hole (short-lived 15-minute access tokens still expire normally).

## 5. Migration strategy

**Alembic**, already in use (`backend/alembic/`, `backend/alembic.ini`) against the same external
Neon database used at runtime — there is no separate migration-only database. Conventions carried
forward from the `Accounts` context and required for every new context:

- One Alembic revision per logical schema change, generated with `uv run alembic revision
  --autogenerate -m "<context>: <change>"` and hand-reviewed before commit (autogenerate misses
  some constraint/index changes and Postgres-specific types).
- Every new table from §2 ships its `organization_id` (or documented one-hop-via-parent) column and
  its cross-tenant-relevant indexes (`ix_<table>_organization_id`, and composite indexes matching the
  existing pattern in `app/accounts/infrastructure/models.py`, e.g. `ix_usuarios_organizacao_perfil`)
  in the **same** revision that creates the table — not as a follow-up migration.
- Migrations run as an explicit deploy step (`uv run alembic upgrade head`) before the new backend
  image starts serving traffic — never `Base.metadata.create_all()` against production, which stays
  a dev/test-only convenience.
- Backward-compatible migration discipline: a migration that would lock a large table or drop a
  column still read by the previous running version is split into an additive step (deploy N) and a
  cleanup step (deploy N+1), consistent with running a single VPS with brief rolling restarts rather
  than a zero-downtime multi-instance fleet.

## 6. Pending rename: Portuguese → English schema (tracked, not yet executed)

The existing `Accounts` tables are Portuguese-named (`organizacoes`, `usuarios`,
`permissoes_modulo`, `organizacao_id` — see `backend/app/accounts/infrastructure/models.py`). ADR-003
and ADR-013 call for renaming to the English vocabulary used throughout this document
(`organizations`, `users`, `module_permissions`, `organization_id`) as part of the `Identity &
Organizations` pivot. This is **implementation work, not an open architectural question** — the
target shape is exactly what §2 lists — tracked in `docs/09-planning/pivot-migration.md` (TODO 1.8)
as an Alembic rename migration (`op.rename_table`, `op.alter_column`) plus an update to every
SQLAlchemy model/enum currently using Portuguese identifiers. All 7 *new* contexts are built directly
against the English names from day one; only `Identity & Organizations` carries this one-time rename
debt.
