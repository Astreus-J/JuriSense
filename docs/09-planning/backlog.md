# Backlog

EPIC → FEATURE → STORY → TASK breakdown, structured to move into Plane without redesign. One EPIC
per roadmap phase. **Phases 0–8 (Foundation through Blockchain/Hackathon Cut) are broken down to
STORY level with acceptance criteria and representative TASKs.** Phases 9–11 (post-hackathon) are
specified at EPIC/FEATURE level only, per instruction — substantive, not empty placeholders, but not
sprint-ready yet.

**Field legend** (every STORY carries all six):
- **Priority**: P0 (blocks the Hackathon Cut / current milestone), P1 (should land in the covering
  milestone but has workable fallback), P2 (nice-to-have, defer without blocking).
- **Dependencies**: other STORY/FEATURE/EPIC IDs, or an external precondition (e.g., a spike result).
- **Risk**: low / medium / high, consistent with `risks.md`'s register.
- **Complexity**: S / M / L / XL, rough relative sizing, not hours.
- **Milestone**: M1–M5 per `milestones.md`.
- **Acceptance criteria**: testable conditions, citing `BR-*` business rules and `docs/03-domain/domain-model.md` entities where applicable.

---

## EPIC-0 — Foundation (Phase 0) — Milestone M1

### FEATURE-0.1 — Repository restructure into 8 bounded contexts

**STORY-0.1.1**: As a developer, I can find every bounded context's code under its own
`app/<context>/{domain,application,infrastructure,api}` package, mirroring the existing layout, so
new contexts have zero structural ambiguity.
- Acceptance criteria: `app/` contains `identity/`, `suppliers/`, `contracts/`, `policy/`,
  `approvals/`, `evidence/`, `ai_services/`, `integrations/`, each with the four standard
  subpackages (even if some are initially empty); `app/api/router.py` aggregates a router from each
  package that has one; `uv run pytest` and `docker compose up -d` both succeed with no behavior
  change from before the restructure.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: none.
- Tasks: create package skeletons; move `app/accounts/` to `app/identity/` as a pure file move (no
  renames yet); update import paths and `router.py`; run full existing test suite to confirm zero
  behavior change.

### FEATURE-0.2 — Identity & Organizations migration

**STORY-0.2.1**: As an Admin, I can create an `Organization` with a name, tax id, and initial plan,
using English field names throughout [`ORG-001`].
- Acceptance criteria: `Organizacao`/`Organization` table and model renamed per `pivot-migration.md`
  (`nome`→`name`, `cnpj`→`tax_id`, etc.); `BR-ORG-002` (tax_id unique within jurisdiction) enforced
  by a DB constraint; all existing organization-creation tests pass under the new names.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M1
- Dependencies: FEATURE-0.1.
- Tasks: rename `Organizacao`→`Organization` model/table/fields; regenerate Alembic migration;
  update all call sites in `application/*.py`; update/rename tests.

**STORY-0.2.2**: As an Admin, I can invite a `User` into my `Organization` with one of the 10
compliance `Role`s (`Admin/Procurement/Legal/Compliance/Privacy/Security/Finance/Approver/Auditor/
Viewer`), reusing the existing invite mechanism [`ORG-002`].
- Acceptance criteria: `Perfil` enum replaced by `Role` with the exact `ADR-003` value set; the
  existing `Convite`/invite token-hash flow works unchanged except for the role value type; an
  invite cannot be created with a role outside the new set (schema/enum-level rejection, not just
  application-layer).
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M1
- Dependencies: STORY-0.2.1.
- Tasks: replace `Perfil` enum values; update `invite_service.py` and its schemas; update
  `api/deps.py`'s `get_current_admin` role check; update invite tests.

**STORY-0.2.3**: As the system, I enforce per-organization plan limits (suppliers, contracts, AI
executions) at creation time, not retroactively, reusing the existing 402-style enforcement pattern
[`ORG-003`].
- Acceptance criteria: `Plano`/`LIMITES_POR_PLANO` replaced with new plan tiers and limit dimensions
  per `docs/02-business/pricing-strategy.md` (`BR-ORG-003`); exceeding a limit blocks new creation
  but never deletes or disables existing data; the existing `LimiteUsuariosAtingidoError`-style
  error pattern is reused for the new limit dimensions.
- Priority: P1 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: STORY-0.2.1.
- Tasks: rename `Plano` enum and `LimitesPlano` dataclass; define new limit dimensions; wire
  enforcement checks at each future creation use case's call site (Suppliers/Contracts/AI, added
  incrementally as those contexts land in later epics).

**STORY-0.2.4**: As an Admin, I can grant a specific `User` permissions beyond their `Role`'s default
grid, reusing the existing per-user permission-override mechanism [`ORG-004`].
- Acceptance criteria: `PermissaoModulo` renamed to an English-named per-user × module × action grid
  (`can_create`/`can_read`/`can_update`/`can_delete`); `Modulo` enum replaced with the new module
  vocabulary (`suppliers/contracts/policies/compliance_reviews/approvals/evidence/integrations/
  organization_settings`); existing override tests pass under new names.
- Priority: P1 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: STORY-0.2.2.
- Tasks: rename `PermissaoModulo` and `Modulo`; update seed-data generation for the new module set;
  update override tests.

**STORY-0.2.5**: As a `User`, I can hold `Membership` in more than one `Organization`, with every
permission check scoped to exactly one active membership at a time [`ORG-005`].
- Acceptance criteria: `BR-ORG-001` holds — no code path assumes a `User` belongs to exactly one
  organization; the multi-tenant lookup pattern already used by `UsuarioRepository`
  (organization-scoped queries) is confirmed to scope correctly when a user has multiple
  memberships.
- Priority: P2 | Risk: low | Complexity: S | Milestone: M1
- Dependencies: STORY-0.2.1.
- Tasks: audit existing single-organization assumptions in `user_service.py`; add a regression test
  with a user holding two organization memberships.

**STORY-0.2.6**: As the system, I no longer collect or validate OAB (Brazilian bar registration)
data anywhere in the user model, since it has no meaning for a compliance-platform user.
- Acceptance criteria: `oab`/`uf_oab` fields, `OabInvalidaError`, `OabJaCadastradaError`,
  `validar_formato_oab()`, and `UsuarioRepository.get_by_oab()` are all removed; no remaining
  reference to OAB anywhere in `app/identity/`; associated OAB test cases deleted.
- Priority: P0 | Risk: medium | Complexity: S | Milestone: M1
- Dependencies: STORY-0.2.1.
- Tasks: remove fields/migration column; remove error classes and their raises; remove and delete
  dependent tests; confirm no remaining import references via a repo-wide grep.

### FEATURE-0.3 — Audit foundation

**STORY-0.3.1**: As the system, I emit an append-only `AuditEvent` for every state-changing
Identity action (`organization.created`, `user.registered`, `membership.invited`,
`membership.accepted`, `membership.revoked`) [`AUD-001`].
- Acceptance criteria: `AuditEvent` entity created (`id`, `event_type`, `actor_id`, `payload`,
  `occurred_at`); an `emit_audit_event()` helper is called from at least the five listed Identity
  use cases; each emitted event is queryable and contains enough payload to reconstruct what
  happened.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: FEATURE-0.2.
- Tasks: create `AuditEvent` model + repository in `app/evidence/`; implement `emit_audit_event()`;
  wire into the five Identity use cases; add a test asserting each action produces exactly one event.

**STORY-0.3.2**: As an Auditor, I cannot update or delete any `AuditEvent`, including as an Admin
[`AUD-002`].
- Acceptance criteria: `BR-EVD-003` holds — no repository method, API route, or admin tool exposes
  an update/delete path for `AuditEvent`; a test attempting a direct update/delete at the repository
  layer fails/raises as expected.
- Priority: P0 | Risk: low | Complexity: S | Milestone: M1
- Dependencies: STORY-0.3.1.
- Tasks: confirm the repository class exposes only `add`/`list`/`get`; add the negative test.

### FEATURE-0.4 — CI and migration baseline

**STORY-0.4.1**: As a developer, I get a red build if `ruff` or `pytest` fails on the renamed
codebase, so the Phase 0 rename can't silently regress.
- Acceptance criteria: CI runs `uv run ruff check .` and `uv run pytest` on every push; both pass
  against the fully renamed schema; a fresh Alembic migration exists and applies cleanly against a
  scratch copy of the external Neon Postgres schema.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M1
- Dependencies: FEATURE-0.2, FEATURE-0.3.
- Tasks: regenerate Alembic migration; add/confirm CI workflow; document the migration rollback
  path in case the Neon schema needs reverting.

---

## EPIC-1 — Core Platform (Phase 1) — Milestone M1

### FEATURE-1.1 — RBAC enforcement across all future modules

**STORY-1.1.1**: As an Admin, when I create an organization, all 10 roles get a sensible default
permission grid across the 8 new modules without manual setup.
- Acceptance criteria: seed data exists for all 10 roles × 8 modules; a newly created organization's
  users inherit their role's default grid immediately; `ADR-012` (RBAC as data) is honored — grids
  are DB rows, not hardcoded branches.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: EPIC-0 (Role/Modulo rename complete).
- Tasks: author the default grid seed dataset; write a seed-loading migration/fixture; add a test
  asserting every role has a non-empty default grid.

**STORY-1.1.2**: As a developer building any future route, I can gate it with a single reusable
permission-check dependency instead of hand-rolling role checks per route.
- Acceptance criteria: a generic `require_permission(module, action)` FastAPI dependency exists,
  modeled on the existing `get_current_admin` pattern; a deny-by-default cross-tenant test (a
  Viewer in Org A cannot write, and no role in Org A can read Org B's data) passes.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M1
- Dependencies: STORY-1.1.1.
- Tasks: implement the generic dependency; write the cross-tenant/cross-role denial test suite;
  document the pattern for reuse by every later context's `api/` layer.

### FEATURE-1.2 — Frontend app shell

**STORY-1.2.1**: As a `User`, I can log in and see a role-appropriate empty dashboard, and switch
between organizations if I hold multiple memberships.
- Acceptance criteria: login/invite-accept screens work end to end against the renamed Identity API;
  an organization switcher is visible and functional when a user has more than one `Membership`
  (`BR-ORG-001`); the dashboard renders without error for each of the 10 roles.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M1
- Dependencies: EPIC-0, FEATURE-1.1.
- Tasks: port the existing Accounts login/invite UI flow into `frontend/`; build the organization
  switcher; build a minimal per-role empty-state dashboard shell.

### FEATURE-1.3 — Object storage adapter

**STORY-1.3.1**: As a developer, I have a single storage abstraction (`put`/`get`/
`generate_presigned_url`) that any future context can use to read/write files, backed by MinIO in
dev and swappable to Cloudflare R2 in production [`ADR-008`].
- Acceptance criteria: MinIO added to `docker-compose.yml`; a storage port interface is defined once
  and has exactly one dev implementation; a smoke test writes and reads back a file through the
  abstraction.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M1
- Dependencies: FEATURE-0.1.
- Tasks: add MinIO service + volume to compose; implement the storage port + MinIO adapter; write
  the smoke test.

### FEATURE-1.4 — Integration scaffold

**STORY-1.4.1**: As an Admin, I can see an `Integration` entity exists as a configuration record
(no real connector yet), establishing the seam future connectors will use [`INT-001`].
- Acceptance criteria: `Integration` entity created (`organization_id`, `provider`, `config`,
  `status`); no code path allows an `Integration` to write directly to a business-domain table
  (verified by a boundary-rule test/lint check, per `docs/04-architecture/components.md`).
- Priority: P2 | Risk: low | Complexity: S | Milestone: M1
- Dependencies: FEATURE-0.1.
- Tasks: create the `Integration` model + minimal CRUD; add a boundary-rule check (lint rule or
  architectural test) preventing direct cross-context ORM writes.

---

## EPIC-2 — Supplier Intelligence (Phase 2) — Milestone M2

### FEATURE-2.1 — Supplier registration and CRUD

**STORY-2.1.1**: As a Procurement user, I can register a `Supplier` with a jurisdiction-specific
identifier (CNPJ for Brazil) [`SUP-001`].
- Acceptance criteria: `Supplier` entity created with `legal_name`, `tax_id`, `jurisdiction`,
  `status` (`prospect/under_review/approved/blocked/inactive`); `BR-SUP-001` holds (belongs to
  exactly one `Organization`); `BR-SUP-002` holds — `tax_id` + `organization_id` unique, enforced by
  a DB constraint, and registering the same tax_id twice in one org returns a clear conflict error.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M2
- Dependencies: EPIC-0 (Organization), EPIC-1 (RBAC on the `suppliers` module).
- Tasks: create `Supplier` model/migration; implement the register-supplier use case; add the
  uniqueness constraint and its conflict-handling test.

**STORY-2.1.2**: As a Procurement user, I can view a list and detail page of my organization's
suppliers, filtered by status.
- Acceptance criteria: list/detail API and frontend screens exist, scoped to the caller's
  organization only (cross-tenant read denial test passes); status filter works for all five
  lifecycle states.
- Priority: P1 | Risk: low | Complexity: M | Milestone: M2
- Dependencies: STORY-2.1.1.
- Tasks: build list/detail endpoints; build frontend supplier list/detail screens.

### FEATURE-2.2 — Supplier verification adapters

**STORY-2.2.1**: As the system, I trigger a `SupplierCheck` against configured external sources
automatically on supplier creation and on manual re-check request [`SUP-002`].
- Acceptance criteria: `SupplierCheck` entity created (`sources_consulted`, `raw_results`,
  `started_at`, `completed_at`, `status`); a check is queued (via Celery, per `ADR-006`) on both
  supplier creation and an explicit re-check API call; a `SupplierCheck` is immutable once
  `completed`.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M2
- Dependencies: STORY-2.1.1.
- Tasks: create `SupplierCheck` model; define the `SupplierVerificationPort` interface; wire a
  Celery task to invoke it on both trigger paths.

**STORY-2.2.2**: As the system, I call the CNPJ registry and CEIS/CNEP/CEPIM sanctions sources
through an adapter behind the `Integrations` context, so no other context depends on a specific
external API shape.
- Acceptance criteria: concrete adapters live in `app/integrations/infrastructure/`, implementing
  `SupplierVerificationPort`; `Suppliers` code only imports the port, never the concrete HTTP
  client (verified by a boundary-rule check); adapter failure/timeout does not crash the check —
  it records a `failed` `SupplierCheck` status instead.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M2
- Dependencies: STORY-2.2.1.
- Tasks: implement CNPJ-registry adapter; implement CEIS/CNEP/CEPIM adapter(s); add
  timeout/retry/failure handling; add a boundary-rule test.

### FEATURE-2.3 — Supplier profile normalization and history

**STORY-2.3.1**: As a Compliance user, I see a `SupplierProfile` that always reflects the most
recent successful `SupplierCheck` [`SUP-003`].
- Acceptance criteria: `SupplierProfile` is replaced (not mutated) on every successful re-check;
  only one active profile exists per supplier at any time.
- Priority: P1 | Risk: low | Complexity: M | Milestone: M2
- Dependencies: STORY-2.2.1.
- Tasks: implement profile-replacement logic on check completion; add a test covering two
  successive successful checks.

**STORY-2.3.2**: As a Compliance user, a sanctions-list hit on any `SupplierCheck` is surfaced as a
non-silent blocking signal on the `Supplier`, never quietly absorbed [`SUP-004`, `BR-SUP-004`].
- Acceptance criteria: a positive sanctions hit sets a visible flag the future `SANC-001` policy
  rule can consume; the flag cannot be cleared without an explicit, audited exception record (the
  exception mechanism itself is built in EPIC-4, but the flag/signal must exist now so it isn't
  retrofitted later).
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M2
- Dependencies: STORY-2.2.2.
- Tasks: add the sanctions-hit signal field/derivation; add a test asserting the flag persists
  across profile replacement until explicitly cleared.

**STORY-2.3.3**: As an Auditor, I can see the full, immutable `SupplierCheck` history for any
supplier, timestamped and in order [`SUP-005`].
- Acceptance criteria: `BR-SUP-003` holds — a `Supplier` cannot reach `approved` status without at
  least one `completed` check newer than any open sanctions flag; check history is queryable and
  never edited after completion.
- Priority: P1 | Risk: low | Complexity: S | Milestone: M2
- Dependencies: STORY-2.2.1.
- Tasks: build the check-history query endpoint/view; add the `BR-SUP-003` status-transition guard.

---

## EPIC-3 — Contract Intelligence (Phase 3) — Milestone M2

### FEATURE-3.1 — Document ingestion and storage

**STORY-3.1.1**: As a Legal user, I can upload a contract document (PDF/DOCX/TXT) [`CON-001`].
- Acceptance criteria: `Document` entity created (`storage_key`, `content_hash`, `mime_type`,
  `uploaded_by`); upload goes through the FEATURE-1.3 storage abstraction; `content_hash` (SHA-256)
  is computed at upload time and never recomputed or mutated afterward.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M2
- Dependencies: EPIC-0, FEATURE-1.3.
- Tasks: create `Document` model; implement upload endpoint; compute and persist `content_hash`.

**STORY-3.1.2**: As the system, I validate and scan every uploaded document for malware/
type-spoofing before processing [`SEC-003`].
- Acceptance criteria: an upload with a mismatched extension/content-type or a known-bad payload
  signature is rejected before it reaches storage; this check runs synchronously on upload, not
  deferred to a later async step.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M2
- Dependencies: STORY-3.1.1.
- Tasks: integrate a file-type/signature validation library; add rejection tests for spoofed
  extension and known-bad-signature cases.

### FEATURE-3.2 — Contract and ContractVersion versioning

**STORY-3.2.1**: As a Legal user, every new negotiation round I upload creates a new
`ContractVersion`, never overwriting a previous one [`CON-002`, `BR-CON-002`].
- Acceptance criteria: `Contract` and `ContractVersion` entities created; a `Contract` belongs to
  exactly one `Supplier` (`BR-CON-001`); uploading a revision against an existing `Contract`
  produces a new `ContractVersion` row and leaves the prior version's data untouched, verified by a
  test that re-uploads and asserts the old version is still readable unchanged.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M2
- Dependencies: STORY-3.1.1, EPIC-2 (Supplier must exist for `Contract.supplier_id`).
- Tasks: create `Contract`/`ContractVersion` models; implement version-creation-on-upload logic;
  add the non-mutation regression test.

### FEATURE-3.3 — AI structured extraction

**STORY-3.3.1**: As the system, I run AI structured extraction on every new `ContractVersion`,
producing the schema in `docs/05-ai/structured-extraction.md` [`CON-003`].
- Acceptance criteria: the AI Gateway abstraction (`ADR-005`) is called with structured-output
  (JSON schema/tool-calling) only — no freeform text parsing anywhere in the pipeline (`AI-001`);
  extraction runs asynchronously via Celery on `ContractVersion` creation.
- Priority: P0 | Risk: high | Complexity: XL | Milestone: M2
- Dependencies: STORY-3.2.1.
- Tasks: build the AI Gateway interface (`extract`/`classify`/`summarize`); implement the OpenAI
  adapter; implement the Anthropic adapter; wire automatic fallback on error/timeout (`AI-003`);
  wire extraction trigger on `ContractVersion` creation.

**STORY-3.3.2**: As a Legal user, every extracted field carries a confidence score and a source
citation back to the document [`AI-002`].
- Acceptance criteria: every field in `extracted_data` has an associated confidence value and a
  document/page/span reference; the confidence-and-citation shape matches
  `docs/05-ai/document-intelligence.md`.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M2
- Dependencies: STORY-3.3.1.
- Tasks: extend the extraction schema with confidence/citation fields; validate provider output
  against the schema before persisting.

**STORY-3.3.3**: As the system, `AI Services` output never directly sets a `Decision` status — only
`Policy & Compliance` may do so [`AI-004`].
- Acceptance criteria: a boundary-rule test/lint confirms no code path in `app/ai_services/` writes
  to any `Decision`-related table or calls any Policy/Compliance application function directly.
- Priority: P0 | Risk: low | Complexity: S | Milestone: M2
- Dependencies: STORY-3.3.1.
- Tasks: add the boundary-rule check to CI; document the rule in `07-engineering/coding-standards.md`
  once that document exists.

### FEATURE-3.4 — Clause provenance and confidence gate

**STORY-3.4.1**: As a Legal user, every AI-identified `Clause` carries a page/span citation back to
its source document, and a clause without provenance cannot be used as evidence [`CON-004`,
`BR-CON-004`].
- Acceptance criteria: `Clause` entity created (`contract_version_id`, `clause_type`, `page`,
  `text_span`, `confidence`); the domain layer rejects creating a `Clause` with a null/missing
  page/span at construction time, not just at review time.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M2
- Dependencies: STORY-3.3.1.
- Tasks: create `Clause` model with a non-null provenance constraint; add a construction-time
  validation test.

**STORY-3.4.2**: As a Legal user, a `ContractVersion` below the minimum extraction confidence is
flagged for mandatory human confirmation before compliance review can proceed [`CON-005`,
`BR-CON-003`].
- Acceptance criteria: a configurable confidence threshold exists; a `ContractVersion` below it is
  marked `needs_confirmation` and blocked from `analyzed` status until a human confirms; the
  frontend surfaces this state clearly on the contract detail screen.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M2
- Dependencies: STORY-3.3.2.
- Tasks: implement the threshold check and `needs_confirmation` state; build the human-confirmation
  UI and endpoint; add a test that a low-confidence version cannot reach `analyzed` without it.

---

## EPIC-4 — Policy Engine (Phase 4) — Milestone M3

### FEATURE-4.1 — ADR-004 expression-language spike

**STORY-4.1.1**: As the engineering team, I know whether `cel-python` cleanly compiles the five
worked example rules in `docs/03-domain/policy-engine.md` before writing production Policy Engine
code.
- Acceptance criteria: a timeboxed spike produces a written result (benchmark numbers, packaging
  notes, and a working proof-of-concept compiling `SANC-001`, `LGPD-001`, `LEGAL-008`, `FIN-003`,
  `FIN-004` to CEL); `ADR-004`'s status is updated to Accepted, or the CEL/JSONLogic priority is
  formally reversed in the ADR.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M3
- Dependencies: EPIC-2, EPIC-3 (spike needs real evidence shapes to test against).
- Tasks: install and benchmark `cel-python`; write the proof-of-concept YAML→CEL compiler for the
  five example rules; document findings and update `ADR-004`.

### FEATURE-4.2 — Policy/PolicyVersion/Rule authoring

**STORY-4.2.1**: As a Compliance user, I can author a `Policy` and its `Rule`s using the YAML DSL
[`POL-001`].
- Acceptance criteria: `Policy`, `PolicyVersion`, `Rule` entities created; rule authoring API
  accepts the YAML shape (`id`, `name`, `when`, `result`, `severity`, `approver_role`) documented in
  `policy-engine.md`; a syntactically invalid rule is rejected with a clear error before it can be
  saved to a draft.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M3
- Dependencies: STORY-4.1.1.
- Tasks: create the three entities/migrations; implement the YAML parser + validator; implement the
  draft-save endpoint.

**STORY-4.2.2**: As a Compliance user, once I publish a `PolicyVersion`, its rules become immutable
forever — editing always creates a new version [`POL-002`, `BR-POL-001`, `BR-POL-002`].
- Acceptance criteria: publishing freezes every `Rule` in the version; an attempted edit of a
  published rule is rejected at the domain layer; only one `PolicyVersion` per `Policy` is
  "current" at a time, enforced by a DB constraint or equivalent guard.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M3
- Dependencies: STORY-4.2.1.
- Tasks: implement the publish action (copy-modify into a new version); add the immutability guard
  and its test; add the single-current-version constraint.

### FEATURE-4.3 — Evaluation context normalizer

**STORY-4.3.1**: As the Policy Engine, I build one flat, typed evaluation context from `Supplier`+
`SupplierProfile`+`SupplierCheck` and `ContractVersion.extracted_data`+`Clause`, so rules never touch
raw AI output or raw documents directly.
- Acceptance criteria: the normalizer produces the exact field shapes documented in
  `policy-engine.md` (`supplier.sanctions_hit`, `contract.liability.type`, `contract.value.brl`,
  `contract.processes_personal_data`, `contract.dpa_present`, etc.); normalization logic lives in
  `Policy & Compliance`'s application layer, not `AI Services` (`BR-CMP-001`).
- Priority: P0 | Risk: high | Complexity: XL | Milestone: M3
- Dependencies: EPIC-2, EPIC-3, STORY-4.1.1.
- Tasks: define the normalized context schema; implement the Supplier-side mapping; implement the
  Contract-side mapping; add a test asserting the context is a pure function of its inputs.

### FEATURE-4.4 — Simulation / dry-run

**STORY-4.4.1**: As a Compliance user, I can run a draft `PolicyVersion` against existing contracts
before publishing, with zero side effects [`POL-003`].
- Acceptance criteria: a simulation run does not create real `ComplianceReview`/`Decision` records
  and does not emit domain events; the simulation result shows, per contract, what would change
  versus the currently published version.
- Priority: P1 | Risk: medium | Complexity: L | Milestone: M3
- Dependencies: STORY-4.2.2, STORY-4.3.1.
- Tasks: implement the simulation execution path (reusing the real evaluator in a non-persisting
  mode); build the simulation-results frontend view.

**STORY-4.4.2**: As a Compliance user, I can grant a time-boxed policy exception for a specific
supplier/contract with mandatory justification and approver sign-off [`POL-004`].
- Acceptance criteria: an exception record is first-class and audited (not a silent rule edit);
  it requires the same `approver_role` the waived rule would have required.
- Priority: P2 | Risk: low | Complexity: M | Milestone: M3
- Dependencies: STORY-4.2.2.
- Tasks: create the exception entity; wire it into the evaluation path as a documented override
  input, not a rule mutation; add an audit event for exception grants.

---

## EPIC-5 — Compliance (Phase 5) — Milestone M3

### FEATURE-5.1 — ComplianceReview execution

**STORY-5.1.1**: As a Compliance user, I can trigger a `ComplianceReview` that evaluates every
applicable `Rule` in the current `PolicyVersion` against normalized evidence [`CMP-001`,
`BR-CMP-001`].
- Acceptance criteria: `ComplianceReview` entity created (`contract_version_id`,
  `policy_version_id`, `status`, `started_at`, `completed_at`); the review always evaluates against
  the FEATURE-4.3 normalized context, never raw AI output; the review is immutable once completed.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M3
- Dependencies: EPIC-4.
- Tasks: create `ComplianceReview` model; implement the review-execution use case; add the
  immutable-once-completed guard.

### FEATURE-5.2 — Aggregation engine (ADR-010)

**STORY-5.2.1**: As a Compliance user, I get a deterministic final status from a set of independent
rule outcomes: any `BLOCK` wins, else any `REVIEW` wins, else `APPROVE` [`CMP-002`, `BR-CMP-002`].
- Acceptance criteria: `RuleEvaluation` entity created with `outcome ∈ {PASS, REVIEW, BLOCK,
  NOT_APPLICABLE}`; the aggregation function is pure and order-independent — a test that permutes
  rule-evaluation order asserts an identical final outcome; a review with zero applicable rules
  correctly defaults to `APPROVE`.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M3
- Dependencies: STORY-5.1.1.
- Tasks: create `RuleEvaluation`/`Risk` models; implement the aggregation function as a pure
  function over an outcome set; write the order-permutation test; write the zero-applicable-rules
  test.

**STORY-5.2.2**: As an Auditor, every `RuleEvaluation` is persisted as append-only and
evidence-linked, never edited or deleted, including by a later override [`CMP-003`, `BR-CMP-003`].
- Acceptance criteria: the repository layer exposes no update/delete path for `RuleEvaluation`;
  every `RuleEvaluation` references its supporting evidence (`Clause`/`SupplierCheck`) via
  `evidence_refs`.
- Priority: P0 | Risk: low | Complexity: S | Milestone: M3
- Dependencies: STORY-5.2.1.
- Tasks: confirm repository exposes only `add`/`list`/`get`; add evidence-ref population logic and
  its test.

### FEATURE-5.3 — Compliance results UI

**STORY-5.3.1**: As a Compliance user, I see WHY / EVIDENCE / POLICY / SOURCE for every triggered
rule on the compliance review results screen, not a bare status.
- Acceptance criteria: the frontend screen renders the final status plus every triggered rule's
  evidence, policy version, and rationale; this matches the product's explainability principle in
  `docs/00-project/overview.md`.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M3
- Dependencies: STORY-5.2.1.
- Tasks: build the review-results API read-model; build the frontend results screen.

---

## EPIC-6 — Approvals (Phase 6) — Milestone M4

### FEATURE-6.1 — ApprovalWorkflow and routing

**STORY-6.1.1**: As a Compliance user, a `REVIEW` outcome is routed to the correct `approver_role`
based on the organization's configured `ApprovalWorkflow` [`APR-001`].
- Acceptance criteria: `ApprovalWorkflow` entity created (`trigger_condition`, ordered `steps`);
  routing correctly selects the highest-severity triggered rule's `approver_role` when multiple
  `REVIEW` rules fire, per `policy-engine.md`'s severity/escalation rule.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M4
- Dependencies: EPIC-5.
- Tasks: create `ApprovalWorkflow` model; implement the routing selection logic; add a
  multiple-REVIEW-rules test.

**STORY-6.1.2**: As a Compliance user, I can configure multi-step approval chains (e.g., Legal then
Director) for high-severity cases [`APR-003`].
- Acceptance criteria: an `ApprovalWorkflow` can have more than one ordered step; a `Decision`
  cannot reach `APPROVE` until every required step in the chain resolves.
- Priority: P1 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-6.1.1.
- Tasks: extend the workflow model to ordered multi-step chains; add a multi-step resolution test.

### FEATURE-6.2 — ApprovalRequest state machine

**STORY-6.2.1**: As an Approver, I can resolve an `ApprovalRequest` only if my `Membership` role
matches its required `approver_role` [`APR-002`, `BR-APR-001`].
- Acceptance criteria: `ApprovalRequest` entity created with a DB-backed state machine
  (`pending`→`approved`/`rejected`/`expired`); a cross-role resolution attempt is rejected and
  covered by a test; every transition emits an `AuditEvent` (`ADR-006`).
- Priority: P0 | Risk: high | Complexity: L | Milestone: M4
- Dependencies: STORY-6.1.1, EPIC-0 FEATURE-0.3 (audit helper).
- Tasks: create `ApprovalRequest` model + state machine; implement the role-match guard; wire the
  audit-event emission on every transition.

**STORY-6.2.2**: As the system, rejecting any required `ApprovalRequest` in a workflow blocks the
overall `Decision` from reaching `APPROVE` without an explicit override [`BR-APR-002`].
- Acceptance criteria: a rejected required step prevents automatic `APPROVE`; only an explicit,
  justified override (FEATURE-6.3) can move past it.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-6.2.1.
- Tasks: implement the rejection-blocks-approval guard; add its test.

**STORY-6.2.3**: As the system, an `ApprovalRequest` that exceeds its configured SLA moves to
`expired` and emits an escalation event [`APR-003` partial, `BR-APR-003`].
- Acceptance criteria: a Celery task checks pending requests against a configurable SLA duration
  (exact default is a documented `TBD` per `BR-APR-003`) and transitions expired ones, emitting an
  escalation `AuditEvent`.
- Priority: P1 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-6.2.1.
- Tasks: implement the Celery SLA-check task; wire the expiration transition and escalation event.

### FEATURE-6.3 — Decision assembly and override

**STORY-6.3.1**: As the system, every completed `ComplianceReview` produces a `Decision` preserving
the exact `PolicyVersion` used [`DEC-001`, `BR-DEC-001`].
- Acceptance criteria: `Decision` entity created (`status`, `valid_until`,
  `supersedes_decision_id`, `overridden`, `override_justification`); created automatically on
  review completion, one-to-one with the `ComplianceReview`.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M4
- Dependencies: STORY-6.2.1.
- Tasks: create `Decision` model; implement automatic creation on review completion.

**STORY-6.3.2**: As an authorized Approver, I can manually override a `Decision` with a mandatory
justification, without deleting the original evaluation record [`DEC-002`, `BR-DEC-003`].
- Acceptance criteria: override requires a non-empty justification string; the original
  `RuleEvaluation` set is untouched; a `decision.overridden` audit event is recorded with
  `original_outcome`, `justification`, `overridden_by`.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-6.3.1.
- Tasks: implement the override endpoint with mandatory-justification validation; wire the
  `decision.overridden` audit event.

### FEATURE-6.4 — Re-evaluation triggers

**STORY-6.4.1**: As the system, I trigger re-evaluation when a `Decision`'s validity expires or its
underlying `ContractVersion`/`PolicyVersion` changes [`DEC-003`, `BR-DEC-004`].
- Acceptance criteria: an expiring `valid_until`, a new `ContractVersion`, or a newly published
  `PolicyVersion` affecting previously-evaluated rules emits `compliance.review_required`; the
  resulting new `Decision` sets `supersedes_decision_id` to the prior one; the prior `Decision` is
  never edited in place (`BR-DEC-002`).
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M4
- Dependencies: STORY-6.3.1.
- Tasks: implement the three trigger conditions; implement the supersedes-chain creation logic; add
  a test covering all three trigger paths.

---

## EPIC-7 — Evidence/Audit (Phase 7) — Milestone M4

### FEATURE-7.1 — EvidencePackage assembly and Merkle root

**STORY-7.1.1**: As the system, I assemble a complete `EvidencePackage` for every `Decision`,
including document hashes, policy version, rule evaluations, and reviewer identities [`EVD-001`].
- Acceptance criteria: `Evidence` and `EvidencePackage` entities created; every `Decision` from
  EPIC-6 gets exactly one `EvidencePackage`; the package includes every field listed in
  `docs/00-project/overview.md`'s Decision Passport description.
- Priority: P0 | Risk: low | Complexity: L | Milestone: M4
- Dependencies: EPIC-6.
- Tasks: create `Evidence`/`EvidencePackage` models; implement the assembly logic pulling from
  Decision/ComplianceReview/RuleEvaluation/Contract/Supplier.

**STORY-7.1.2**: As an Auditor, I can recompute an `EvidencePackage`'s `merkle_root` at any time and
get the same value [`EVD-002`, `BR-EVD-001`].
- Acceptance criteria: a fixed, documented canonical ordering of evidence items is used;
  recomputing the Merkle root from the persisted `Evidence` set always matches the stored value.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-7.1.1.
- Tasks: implement the deterministic Merkle-root computation with documented canonical ordering;
  add a recomputation-matches test.

### FEATURE-7.2 — Full audit catalog coverage

**STORY-7.2.1**: As an Auditor, I can see an `AuditEvent` for every state-changing action across
Identity, Suppliers, Contracts, Policy, Compliance, and Approvals built so far [`AUD-001`].
- Acceptance criteria: the event catalog in `docs/03-domain/audit.md` is cross-checked against
  actual emitted events from every EPIC 0–6 use case; any gap found is closed by adding the missing
  `emit_audit_event()` call.
- Priority: P0 | Risk: medium | Complexity: L | Milestone: M4
- Dependencies: EPIC-0 through EPIC-6.
- Tasks: audit every use case built so far for a missing audit-event emission; close each gap
  found; add a coverage test asserting every documented event type has at least one emission
  test.

### FEATURE-7.3 — Decision Passport

**STORY-7.3.1**: As a Compliance user or external auditor, I can view a complete, reproducible
"why was this approved?" narrative for any `Decision`, months or years later.
- Acceptance criteria: the Decision Passport view renders decision id, supplier, contract, document
  hashes, policies evaluated (with version), rules triggered, external sources consulted, AI
  executions (model/prompt version), reviewers, final decision, and timestamp, all sourced from the
  immutable records built in EPIC-2 through EPIC-7.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M4
- Dependencies: STORY-7.1.1.
- Tasks: build the Decision Passport read-model API; build the frontend view.

---

## EPIC-8 — Blockchain (Phase 8, Hackathon Cut) — Milestone M4/M5

### FEATURE-8.1 — AnchoringProvider spike (ADR-007)

**STORY-8.1.1**: As the engineering team, I know which `AnchoringProvider` adapter to ship for the
hackathon demo before building against it in production code.
- Acceptance criteria: a timeboxed spike attempts Constellation Network first, falls back to an EVM
  L2 testnet if Constellation's SDK/tooling proves too heavy for the remaining timeline, and
  evaluates ICP/Caffeine AI only if it shows unusually low integration effort; `ADR-007`'s status is
  updated to Accepted with the chosen adapter and rationale documented.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M4
- Dependencies: EPIC-7.
- Tasks: attempt Constellation SDK integration; if infeasible within budget, attempt the EVM L2
  testnet path (viem/ethers + minimal hash-anchoring contract); document findings and update
  `ADR-007`.

### FEATURE-8.2 — BlockchainAnchor implementation

**STORY-8.2.1**: As the system, I anchor an `EvidencePackage`'s hash via the chosen
`AnchoringProvider`, submitting only the hash, never raw contract/supplier data [`EVD-003`,
`EVD-004`, `BR-EVD-002`].
- Acceptance criteria: `BlockchainAnchor` entity created (`provider`, `anchor_ref`, `submitted_at`,
  `proof`); `submit_hash`/`get_proof`/`verify` implemented against the chosen adapter; a test
  confirms no raw document/personal-data field ever appears in the anchor payload.
- Priority: P0 | Risk: high | Complexity: L | Milestone: M4
- Dependencies: STORY-8.1.1.
- Tasks: create `BlockchainAnchor` model; implement the interface against the chosen adapter; add
  the payload-content test.

**STORY-8.2.2**: As the system, if no chain integration lands in time, I fall back to a signed hash
+ timestamp published to a public, git-backed transparency log, clearly labeled as a fallback, not
a blockchain anchor.
- Acceptance criteria: the fallback implements the same `AnchoringProvider` interface so nothing
  above it in the stack changes; the product UI and the hackathon submission materials both clearly
  label this mode as a fallback verification mechanism.
- Priority: P0 (activates only if STORY-8.1.1/8.2.1 miss the deadline) | Risk: medium | Complexity: M
  | Milestone: M4
- Dependencies: STORY-8.1.1 (as the documented contingency, per `risks.md`).
- Tasks: implement the signed-hash + transparency-log adapter; add the explicit fallback label in
  both API response and UI copy.

### FEATURE-8.3 — Public verification page

**STORY-8.3.1**: As a third party (auditor, counterparty, hackathon judge), I can verify an
anchored `Decision`'s hash without logging in [`EVD-003`].
- Acceptance criteria: a public page accepts a decision/evidence reference or raw hash, calls
  `verify()`, and renders a plain-language result; the page works correctly whether the real chain
  adapter or the fallback (FEATURE-8.2.2) is in effect.
- Priority: P0 | Risk: medium | Complexity: M | Milestone: M4
- Dependencies: STORY-8.2.1.
- Tasks: build the public verification API endpoint (no auth); build the public frontend page.

### FEATURE-8.4 — Landing page rewrite

**STORY-8.4.1**: As a prospective customer visiting the marketing site, I see JuriSense Gate's
actual positioning, features, and pricing — not the legacy legal-ERP copy.
- Acceptance criteria: `frontend/src/lib/landing-data.ts` is fully rewritten per
  `pivot-migration.md` item (d) — `features`, `plans`, `steps`, `faqs`, `allPlansInclude` all
  replaced; only the `contact` object and TypeScript type declarations are carried over unchanged.
- Priority: P0 | Risk: low | Complexity: M | Milestone: M4/M5
- Dependencies: `docs/02-business/pricing-strategy.md` existing with final plan tiers.
- Tasks: rewrite `features`; rewrite `plans`; rewrite `steps`/`faqs`/`allPlansInclude`; visual QA
  against the existing landing page components.

### FEATURE-8.5 — Hackathon submission prep

**STORY-8.5.1**: As the team, I submit a complete, working demo before judging opens on
2026-11-05.
- Acceptance criteria: pitch deck, demo video (covering the full Supplier→Contract→Policy→
  Compliance→Approval→Decision→Evidence→Anchor→Verify pipeline), and an updated root `README.md`
  are all complete; the public verification page (FEATURE-8.3) is live and stable through the
  2026-12-05 judging close.
- Priority: P0 | Risk: high | Complexity: M | Milestone: M5
- Dependencies: all of EPIC-8.
- Tasks: record the demo video; build the pitch deck; update root `README.md`; file the submission.

---

## === HACKATHON CUT — everything below is post-hackathon, EPIC/FEATURE level only ===

## EPIC-9 — Integrations (Phase 9) — post-hackathon

Extends the `Integrations` bounded context from the Phase 1 configuration-only scaffold into real,
production-usable connectors, unblocking customers who need JuriSense Gate to participate in their
existing procurement and e-signature workflows rather than acting as an isolated tool.

- **FEATURE-9.1 — Outbound webhooks**: implement `INT-002`'s four lifecycle webhooks
  (`supplier.review.completed`, `contract.review.completed`, `approval.required`,
  `decision.completed`) with retry/backoff and HMAC signature verification, so third-party systems
  can react to compliance events reliably and securely.
- **FEATURE-9.2 — DocuSign integration**: connect contract execution to DocuSign so an
  `APPROVE`d contract can move directly to e-signature without leaving the platform, closing the
  loop between compliance decision and actual contract execution.
- **FEATURE-9.3 — Slack notification connector**: push approval-required and decision-completed
  notifications into a customer's Slack workspace, meeting Procurement/Legal teams where they
  already work instead of requiring them to check the platform proactively.
- **FEATURE-9.4 — ERP connector groundwork**: lay the adapter groundwork (not a full integration)
  for future accounts-payable/procurement-system sync, informed by whichever ERP systems the first
  real pilot customers actually use.

## EPIC-10 — Enterprise (Phase 10) — post-hackathon

Hardens the platform for larger, more regulated buyers who need real billing, stronger tenant
isolation guarantees, and enterprise-grade identity — none of which block the hackathon demo but all
of which are prerequisites for closing a real enterprise contract.

- **FEATURE-10.1 — Payment gateway integration**: resolve `ADR-014`'s deliberately deferred payment
  decision by integrating Stripe or a Brazilian equivalent, converting the existing
  trial/active/past_due/cancelled/expired state machine from a modeled-but-unenforced concept into
  real, billed subscriptions.
- **FEATURE-10.2 — Row-Level Security hardening**: add PostgreSQL RLS on top of the existing logical
  multi-tenancy (`organization_id` filtering) as defense-in-depth, addressing the v1.x hardening
  item `ADR-003` explicitly deferred rather than skipped.
- **FEATURE-10.3 — Custom and versioned roles**: let an enterprise customer define roles beyond the
  seeded 10, and version role definitions the way `PolicyVersion` is versioned, for organizations
  whose internal approval structure doesn't map cleanly onto the default set.
- **FEATURE-10.4 — SSO for enterprise identity providers**: add SAML/OIDC support so enterprise
  buyers can provision and deprovision users through their existing IdP instead of the platform's
  own invite flow.

## EPIC-11 — International (Phase 11) — post-hackathon

Extends JuriSense Gate beyond Brazil via the Core Platform / Jurisdiction Pack separation the domain
model and Policy Engine were deliberately designed to support from Phase 2/4 onward, realizing the
long-term vision described in `docs/00-project/overview.md`.

- **FEATURE-11.1 — Jurisdiction Pack architecture**: formalize the Core Platform vs. Jurisdiction
  Pack boundary as a real code seam (not just a documented intent), so jurisdiction-specific
  identifier schemes, sanctions sources, and policy rule packs can be swapped without touching core
  domain logic.
- **FEATURE-11.2 — First non-Brazil jurisdiction pack**: build a complete pack (US or EU, exact
  choice `TBD` pending commercial priority) including its own supplier-identity scheme, sanctions
  sources (e.g., OFAC or an EU equivalent in place of CEIS/CNEP/CEPIM), and a GDPR-flavored policy
  rule pack in place of the LGPD-flavored one.
- **FEATURE-11.3 — Localized frontend**: translate and adapt the frontend copy for the new market,
  building on the same content structure established by the Phase 8 landing-page rewrite.
