# Database Standards

Conventions for the single external PostgreSQL database (Neon-managed, `docs/00-project/overview.md`)
shared by all 8 bounded contexts (ADR-002: one deployable, one database — no schema-per-context or
database-per-context split).

## Migration workflow (Alembic)

- Alembic is already wired (`backend/alembic/`, `backend/alembic.ini`) and is the only way schema
  changes reach the database — no manual `ALTER TABLE` against Neon, in any environment.
- One shared `alembic/versions/` history for the whole application, not one per bounded context —
  consistent with one database for the modular monolith. Migration filenames/revision messages are
  prefixed with the owning context for readability: `add_suppliers_table`, `add_policy_versions_table`.
- Every migration is reviewed for two things beyond correctness: (1) does it lock the table for a
  long time on a large existing table (use `CONCURRENTLY` for index creation on tables expected to
  have production data — not a concern yet, but the habit starts now), and (2) does it violate any
  of the append-only/no-UPDATE rules below.
- `uv run alembic revision --autogenerate -m "<message>"` to generate, followed by a manual review
  of the generated diff — autogenerate is a draft, not a commit-as-is tool, particularly for the
  versioned-entity and append-only enforcement below, which autogenerate does not know to add.
- A migration is checked in CI (`docs/07-engineering/ci-cd.md`'s migration-check stage): the CI
  pipeline runs `alembic upgrade head` against a throwaway database to catch a migration that only
  works against a developer's already-drifted local schema.
- Migrations are forward-only in shared environments (staging/production) — a bad migration is fixed
  with a new, corrective migration, not by editing/deleting an already-applied one. Only a migration
  that has never been applied outside a developer's own machine may be edited in place.

## Naming conventions

**All new tables and columns are English**, per the project-wide rule in
`docs/07-engineering/coding-standards.md`. The table below contrasts the standard with the existing,
grandfathered `Accounts` schema so the debt is visible and not silently perpetuated:

| Concept | New standard (English) | Existing `Accounts` (Portuguese — migration debt) |
|---|---|---|
| Tenant table | `organizations` | `organizacoes` |
| User table | `users` | `usuarios` |
| Tenant FK column | `organization_id` | `organizacao_id` |
| Password hash column | `password_hash` | `senha_hash` |
| Created-at column | `created_at` | `criado_em` |
| Updated-at column | `updated_at` | `atualizado_em` |
| Active flag | `active` (or a derived property, per ADR-013) | `ativo` |
| Enum: role | `role` | `perfil` |

New tables (`suppliers`, `contract_versions`, `policy_versions`, `rule_evaluations`,
`approval_requests`, `decisions`, `evidence_packages`, `audit_events`, etc.) use exactly the English
column names in the left column above, plus:

- Table names: plural, `snake_case` (`suppliers`, not `Supplier` or `supplier`).
- Primary key: `id` (UUID, `default=uuid.uuid4`, matching the existing pattern in
  `app/accounts/infrastructure/models.py`).
- Foreign keys: `<referenced_table_singular>_id` (`supplier_id`, `contract_id`, `policy_version_id`).
- Timestamps: `created_at` always; `updated_at` only on tables that are actually mutated in place
  (most new tables are versioned/append-only per below and therefore have **no** `updated_at` at
  all — its presence on a table is itself a signal the table is mutable).
- Enum-like columns: stored as `String` with an application-level Python `Enum` (matching the
  existing `Plano`/`Perfil` pattern in `app/accounts/domain/constants.py`), not a native Postgres
  `ENUM` type — this keeps adding a new enum value a zero-downtime application deploy instead of a
  blocking `ALTER TYPE`.
- Renaming an existing Portuguese column is **out of scope for organic feature work** — it is
  sequenced, tracked work in `docs/09-planning/pivot-migration.md` (covering the Alembic
  expand/contract pattern needed to rename a live column without downtime: add new column → dual-write
  → backfill → cut reads over → drop old column). Do not rename a column as a drive-by change inside
  an unrelated PR.

## Multi-tenancy column convention

Every tenant-owned table carries **`organization_id`** (ADR-003, ADR-015), with these concrete rules:

- `organization_id` is `NOT NULL` on every tenant-owned table (the few tables that are genuinely
  system-level, like `roles`' default seed data, are the explicit exception, not the default).
- `organization_id` is **always indexed**, typically as the leading column of a composite index that
  matches the table's most common query shape (e.g. `Index("ix_suppliers_organization_status",
  "organization_id", "status")`), following the existing
  `Index("ix_usuarios_organizacao_perfil", "organizacao_id", "perfil")` pattern.
- `organization_id` is a foreign key to `organizations.id` with `ON DELETE RESTRICT` (or no cascade
  at all) — an organization is soft-deleted, never hard-deleted while it owns rows (`Organization`
  invariant in `docs/03-domain/domain-model.md`), so cascading deletes are never the right behavior.
- **Every repository method that reads or writes a tenant-owned table takes the caller's
  `organization_id` as an explicit, non-optional parameter and filters by it** — this is enforced at
  the repository layer, not left to be remembered per-query at the API layer (ADR-003 "enforced at
  the repository layer"). A repository method with no `organization_id` parameter reading from a
  tenant-owned table is a code-review-blocking defect, not a style nit.
- Postgres Row-Level Security (RLS) as defense-in-depth is a deferred v1.x hardening item
  (`docs/09-planning/backlog.md`, per ADR-003) — not implemented yet, so the repository-layer filter
  above is currently the **only** enforcement mechanism and must never be skipped "just this once."

## Versioned-entity pattern (immutability at the DB level)

`PolicyVersion`, `ContractVersion`, `Rule` (once its `PolicyVersion` is published), `RuleEvaluation`,
`Decision`, `Evidence`, and `EvidencePackage` are all immutable-once-created domain entities
(`docs/03-domain/domain-model.md`, `ADR-010`). The database enforces this, not just application-layer
discipline:

- The application's database role (the credential the FastAPI app connects with) is granted
  **`INSERT`, `SELECT` only — no `UPDATE`, no `DELETE`** — on every versioned-entity table
  (`policy_versions`, `rules`, `contract_versions`, `rule_evaluations`, `decisions`, `evidence`,
  `evidence_packages`). This is a real Postgres `GRANT`/`REVOKE`, not a convention documented only in
  code: `REVOKE UPDATE, DELETE ON policy_versions FROM jurisense_app;` in the relevant Alembic
  migration.
- Superseding is modeled as a **new row with a pointer back**, never a mutation:
  `Decision.supersedes_decision_id` references the row it replaces; there is no "current" flag
  flipped on the old row via `UPDATE`. Where a "what's current" query is needed (e.g., "the current
  `PolicyVersion` for this `Policy`"), it is a `SELECT ... ORDER BY version_number DESC LIMIT 1` (or
  a dedicated pointer table that itself only gets a new row on change), never an `UPDATE` of an
  `is_current` boolean on the historical row.
- A table needing a genuine mutable field (e.g. `Policy.status`, `Organization.plan`, mutable
  *container* metadata, not the versioned content itself) is deliberately **not** in the
  no-`UPDATE`-grant set — the distinction is: containers (`Policy`, `Organization`, `Contract`,
  `Supplier`) are mutable metadata pointers; their versioned children are not. This split is
  intentional and mirrors the domain model's own container/version split.
- Tests verify this at the database level, not just the application level: a test that attempts a
  raw `UPDATE` against a versioned table using the app's own database role must fail with a Postgres
  permission error, exercised in the `policies` and `evidence` context's test suites
  (`docs/07-engineering/testing-strategy.md`).

## Audit table append-only enforcement

`AuditEvent` (`audit_events` table, `Evidence & Audit` context) is the strictest case — it is the
system's memory of "what happened," and its trustworthiness depends on nothing, including an Admin
role, being able to alter it:

- Same `REVOKE UPDATE, DELETE` grant as the versioned-entity tables above, applied to `audit_events`
  specifically and enforced from the very first migration that creates the table, not added later.
- No API endpoint anywhere in the system exposes an update or delete operation on an audit event —
  this is a product requirement (`BR-EVD-003`: "the audit log has no update or delete operation
  exposed anywhere in the system, including to Admin roles"), not only a DB-permission backstop.
- `audit_events.id` is a UUID that is also **monotonically ordered** (e.g. UUIDv7 or a ULID stored as
  the primary key, or a separate `BIGSERIAL sequence_number` column alongside a UUID `id`) so the
  event log's insertion order is queryable and verifiable independent of `occurred_at` wall-clock
  time, which is not trustworthy alone for ordering under clock skew.
- `audit_events.organization_id` is nullable (system-level events, e.g. an org-independent security
  event) but every tenant-scoped event carries it, indexed, for the same reasons as any other
  tenant-owned table above.
- Because `EvidencePackage.merkle_root` must be deterministically recomputable from its `Evidence`
  set at any time (`BR-EVD-001`), the same append-only guarantee that protects `audit_events`
  protects `evidence` — a mutated evidence row would silently break every past Merkle-root
  recomputation and invalidate blockchain anchors retroactively, which is precisely the failure mode
  the anchoring layer exists to make detectable and impossible to hide (`ADR-007`).

## Indexing checklist for a new tenant-owned table

Every new migration adding a tenant-owned table is reviewed against this checklist, not just "does
it have a primary key":

1. `organization_id` present, `NOT NULL`, indexed (leading column of at least one index).
2. Foreign keys indexed (Postgres does not auto-index FKs).
3. Any column used in a `WHERE` clause by an existing or planned query path has a matching index —
   added when the query is written, not spot-fixed later from a slow-query log, given how central
   query patterns (org + status, org + type) are already known from the domain model.
4. Versioned/append-only tables reviewed against the `REVOKE UPDATE, DELETE` checklist above.
5. Unique constraints match the domain's stated invariants exactly (e.g. `UniqueConstraint("tax_id",
   "organization_id")` for `suppliers`, mirroring `BR-SUP-002`) — a missing unique constraint that
   the domain claims as an invariant is a bug, not a future improvement.
