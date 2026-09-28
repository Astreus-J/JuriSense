# Roadmap

Twelve phases, Phase 0 (Foundation) through Phase 11 (International). The **Hackathon Cut** is an
explicit scope line drawn after **Phase 8**: everything through Phase 8 must be real, working, and
demoable before the BLI Legal Tech Hackathon 2 / Legal Hack 2026 judging window opens on
**2026-11-05** (judging runs through 2026-12-05, awards 2026-12-12). Phases 9–11 are real,
committed post-hackathon product work — not padding — but they are explicitly out of scope for the
hackathon submission.

Each phase lists: **Objective**, **Deliverables** (citing entities from `docs/03-domain/domain-model.md`
and requirement IDs from `docs/01-product/functional-requirements.md`), **Dependencies**, **Exit
criteria**, **Risks**, and **What becomes possible after**. Cross-reference `dependencies.md` for the
full dependency graph, `milestones.md` for calendar-relative timing, `risks.md` for the consolidated
risk register, and `backlog.md` for the EPIC/FEATURE/STORY/TASK breakdown of each phase.

Bounded contexts referenced throughout: **Identity & Organizations, Suppliers, Contracts &
Documents, Policy & Compliance, Approvals & Decisions, Evidence & Audit, AI Services, Integrations**
(`docs/03-domain/domain-model.md`). Note that AI Services does not get its own roadmap phase — it is
built as an embedded capability of Phase 3 (Contract Intelligence) and reused by later phases, per
the context-boundary rule that AI Services never independently decides a compliance outcome
(`docs/04-architecture/components.md`, `AI-004`).

---

## Phase 0 — Foundation

**Objective**: Stabilize the repository into the 8-bounded-context modular-monolith layout
(`ADR-002`), migrate the existing, tested, security-audited `Accounts` code into the new `Identity &
Organizations` context, and establish the `AuditEvent` foundation that every later context depends
on for append-only traceability.

**Deliverables**:
- `app/` restructured into 8 packages (`identity`, `suppliers`, `contracts`, `policy`, `approvals`,
  `evidence`, `ai_services`, `integrations`), each following the existing
  domain/application/infrastructure/api layering (`ADR-001`, `ADR-002`).
- Identity & Organizations migration per `pivot-migration.md`: `Organizacao` → `Organization`,
  `Usuario` → `User`, `Perfil` → `Role` (new `ADR-003` values: Admin, Procurement, Legal,
  Compliance, Privacy, Security, Finance, Approver, Auditor, Viewer), `Modulo` → new module
  vocabulary (`suppliers`, `contracts`, `policies`, `compliance_reviews`, `approvals`, `evidence`,
  `integrations`, `organization_settings`), `organizacao_id` → `organization_id`, and every other
  Portuguese identifier renamed to English. `oab`/`uf_oab` fields and `OabInvalidaError`/
  `OabJaCadastradaError` are removed (`ORG-001`–`ORG-005`).
- `AuditEvent` entity + append-only repository + an `emit_audit_event()` application-layer helper,
  wired into at least the Identity events (`user.registered`, `membership.invited`,
  `membership.accepted`, `membership.revoked`) (`AUD-001`, `AUD-002`).
- Alembic migration baseline regenerated under the new English schema against the external Neon
  Postgres; CI gate (`uv run ruff check .`, `uv run pytest`) green on the renamed codebase.
- Docker Compose / `.env` references updated for the renamed schema (naming only, no functional
  change to the VPS/Neon/Redis hosting model already in place).

**Dependencies**: none — this is the first phase. It consumes the existing, already-tested and
audited `Accounts` code (`docs/auditorias/sprint-01.md`, `sprint-02.md`) as its starting point.

**Exit criteria**: every existing Accounts test passes unmodified in behavior (only names changed)
against the renamed schema; a cross-tenant-access test passes for `Organization` isolation
(`ADR-003`, `SEC-001`); the `AuditEvent` table exists and receives at least one real event type in
practice; the sprint's `ADR-016` security-audit gate passes with no open critical/high findings.

**Risks**: renaming ~2,100 lines of Portuguese, legal-domain-specific identifiers without silently
breaking the ~700 lines of existing passing tests or reintroducing a tenant-isolation regression
(see `risks.md` — legacy-code migration risk). Schema rename on the external, shared Neon database
requires careful, reversible Alembic migration sequencing (no downtime tooling exists yet).

**What becomes possible after**: every subsequent bounded context (Suppliers, Contracts, Policy,
Approvals, Evidence) can be built against a stable `Organization` / `User` / `Role` /
`AuditEvent` substrate instead of legal-ERP-shaped ground beneath it. Phase 1 begins.

---

## Phase 1 — Core Platform

**Objective**: Build the minimum cross-cutting platform every business context needs: enforced
RBAC, a working frontend app shell, and the object-storage adapter groundwork — before any
business-domain feature work starts.

**Deliverables**:
- RBAC-as-data seed (`ADR-003`, `ADR-012`): default module × action grid for all 10 roles across
  the 8 new modules, reusing the existing `PermissaoModulo` pattern; a reusable permission-check
  FastAPI dependency for every future router; admin override of per-user grants (`ORG-004`).
- Frontend app shell in `frontend/`: authenticated layout, organization switcher (`BR-ORG-001`
  — a `User` may hold `Membership` in more than one `Organization`), login/invite-accept screens
  ported from the existing Accounts UI flow, empty role-appropriate dashboard.
- s3mock added to `docker-compose.yml` for local dev object storage, matching the target Cloudflare
  R2 production backend (`ADR-008`); a single storage abstraction used by any future
  Contracts/Evidence write.
- `Integration` entity scaffold (config-only, no real connector) so the `Integrations` context
  exists as a seam from day one (`INT-001` boundary rule — never direct writes to business tables).

**Dependencies**: Phase 0 (`Organization`, `User`, `Role`, `AuditEvent` must exist first).

**Exit criteria**: an Admin can invite a user into an org with one of the 10 compliance roles, and
that user sees a role-appropriate empty dashboard on login; a deny-by-default RBAC test (a
`Viewer` cannot write, a `Procurement` user of Org A cannot read Org B's data) passes; the backend
dev container can read/write to the local s3mock bucket.

**Risks**: RBAC default-grid design may not anticipate every context's real permission needs and
require re-seeding once Suppliers/Contracts land; the frontend runs on a pre-release Next.js 16
whose APIs diverge from training-data conventions (see `frontend/AGENTS.md`), which can slow
screen-building more than a stable-Next.js estimate would suggest.

**What becomes possible after**: Suppliers (Phase 2) and Contracts & Documents (Phase 3) can be
built on a working tenant-isolated, RBAC-enforced, storage-capable platform, and — because neither
depends on the other — can proceed **in parallel** (see `dependencies.md`).

---

## Phase 2 — Supplier Intelligence

**Objective**: Implement the `Suppliers` bounded context end to end: registration, external
verification, and normalized profile state.

**Deliverables**:
- `Supplier`, `SupplierProfile`, `SupplierCheck` entities and tables (`SUP-001`–`SUP-005`).
- Verification adapters for CNPJ registry status and Brazilian sanctions/restriction lists
  (CEIS/CNEP/CEPIM), implemented behind an `Integrations`-context adapter interface so no other
  context depends on a specific external API shape (`INT-001` boundary rule).
- Supplier CRUD API and frontend supplier list/detail screens, including manual re-check trigger.
- `BR-SUP-002` (tax_id + organization_id uniqueness) and `BR-SUP-004` (a sanctions hit forces the
  supplier toward the `BLOCK` path via rule `SANC-001`, non-silently) enforced.

**Dependencies**: Phase 0 (`Organization`), Phase 1 (RBAC enforcement on the new `suppliers`
module). Does **not** depend on Phase 3.

**Exit criteria**: a Procurement-role user registers a `Supplier` with a CNPJ, a `SupplierCheck`
runs automatically on creation, and the resulting `SupplierProfile` reflects registry status and
any sanctions hit; `SupplierCheck` history is immutable and fully queryable; `supplier.created`,
`supplier.updated`, `supplier.status_changed` audit events are emitted.

**Risks**: external registry/sanctions source availability, rate limits, or format drift
(mitigation: adapter interface isolates the blast radius, plus a manual-entry fallback path); CNPJ
validation edge cases (invalid check digits, inactive/suspended registrations).

**What becomes possible after**: `Policy & Compliance` (Phase 4/5) has real, normalized supplier
evidence to evaluate rules against. Can be built in parallel with Phase 3.

---

## Phase 3 — Contract Intelligence

**Objective**: Implement the `Contracts & Documents` bounded context and the embedded `AI Services`
extraction pipeline: ingestion, versioning, structured extraction, clause-level provenance.

**Deliverables**:
- `Document`, `Contract`, `ContractVersion`, `Clause` entities (`CON-001`–`CON-005`).
- Upload API for PDF/DOCX/TXT wired to the Phase 1 storage abstraction; `content_hash` computed
  and immutable on upload (`ADR-008`).
- AI Services extraction pipeline v1: AI Gateway abstraction (`ADR-005`) calling structured-output
  extraction against the schema in `docs/05-ai/structured-extraction.md`, attaching confidence and
  page/span provenance to every field/clause (`AI-001`, `AI-002`, `CON-004`).
- Minimum-confidence gate: a `ContractVersion` below threshold is flagged for mandatory human
  confirmation before it can proceed to compliance review (`CON-005`, `BR-CON-003`).
- Frontend contract upload/detail screens with clause highlighting and citation back to source page.

**Dependencies**: Phase 0 (`Organization`), Phase 1 (storage abstraction). Does **not** depend on
Phase 2 — the two can run **in parallel**.

**Exit criteria**: a Legal-role user uploads a contract PDF and gets back a new `ContractVersion`
with structured extracted fields and page/span-cited `Clause` records; low-confidence fields are
visibly flagged rather than silently accepted; re-uploading a revision creates a new
`ContractVersion` without touching the previous one (`BR-CON-002`).

**Risks**: AI extraction accuracy on real Brazilian contract language, formatting, and scanned/
image-only PDFs (see `risks.md`); provider cost/latency at extraction volume is untuned before real
usage data exists (`ADR-005` leaves exact model selection as a documented TBD).

**What becomes possible after**: `Policy & Compliance` has real, structured contract evidence.
Together, Phases 2 and 3 unblock Phase 4.

---

## Phase 4 — Policy Engine

**Objective**: Implement the authoring/versioning half of `Policy & Compliance`: the YAML rule DSL,
the `ADR-004` CEL-compilation spike, and simulation.

**Deliverables**:
- `Policy`, `PolicyVersion`, `Rule` entities and immutable-on-publish versioning (`POL-001`,
  `POL-002`, `BR-POL-001`, `BR-POL-002`).
- The `ADR-004` technical spike: `cel-python` performance/packaging validation, the YAML `when` →
  CEL compiler, and a decision on whether JSONLogic is needed sooner (for a future no-code rule
  builder) than originally planned. This spike's outcome moves `ADR-004` from "Proposed" to
  "Accepted" (or reverses the CEL/JSONLogic priority).
- The normalized evaluation-context builder described in `docs/03-domain/policy-engine.md`
  (`supplier.sanctions_hit`, `contract.liability.type`, `contract.value.brl`, etc.), owned by
  `Policy & Compliance`'s application layer, not `AI Services`.
- Rule authoring API and a minimal frontend rule editor (raw YAML first; a visual/no-code builder
  is explicitly out of scope for the Hackathon Cut).
- Simulation/dry-run engine: run a draft `PolicyVersion` against existing contracts without
  creating real `ComplianceReview`/`Decision` records (`POL-003`).

**Dependencies**: Phase 2 **and** Phase 3 (needs both supplier and contract evidence shapes to
normalize against — this is the first point where the two parallel tracks converge). Phase 1
(RBAC, since `approver_role` on a `Rule` references a `Role`).

**Exit criteria**: an organization can author the `SANC-001`/`LGPD-001`/`FIN-003`/`FIN-004`/
`LEGAL-008` example rules from `docs/03-domain/policy-engine.md` in YAML, publish them as an
immutable `PolicyVersion`, and run a dry-run simulation against existing `ContractVersion`s with no
side effects; `ADR-004`'s status is updated based on the spike's findings.

**Risks**: policy-engine expressiveness risk — the CEL/JSONLogic spike could reveal the chosen
language cannot cleanly express nested or cross-entity conditions the DSL promises (see `risks.md`
for the fallback plan). Hiding CEL's raw syntax from non-technical policy authors is a real UX
problem, not just a technical one.

**What becomes possible after**: Phase 5 can evaluate real rules against real, normalized evidence.

---

## Phase 5 — Compliance

**Objective**: Implement the evaluation/aggregation half of `Policy & Compliance`: running rules and
turning their outcomes into one explainable, deterministic status per `ADR-010`.

**Deliverables**:
- `ComplianceReview`, `RuleEvaluation`, `Risk` entities (`CMP-001`–`CMP-003`).
- The `ADR-010` aggregation engine: any `BLOCK` → `BLOCK`; else any `REVIEW` → `REVIEW` (with the
  required approver being the highest-severity triggered rule's `approver_role`); else `APPROVE`
  (`BR-CMP-002`).
- Append-only, evidence-linked `RuleEvaluation` persistence — never edited, including by later
  overrides (`BR-CMP-003`).
- Frontend compliance review results screen surfacing WHY / EVIDENCE / POLICY / SOURCE for every
  triggered rule, per the product's core explainability promise (`docs/00-project/overview.md`).

**Dependencies**: Phase 4 (needs a published `PolicyVersion` and the evaluation-context normalizer).

**Exit criteria**: running a `ComplianceReview` against a real `Supplier` + `ContractVersion` +
`PolicyVersion` combination produces a deterministic, explainable status with linked evidence for
every triggered rule; a test that permutes rule-evaluation order and asserts an identical final
outcome passes, proving `BR-CMP-002`'s order-independence; a review with zero applicable rules
correctly defaults to `APPROVE` rather than erroring.

**Risks**: aggregation edge cases around `NOT_APPLICABLE` outcomes and empty rule sets; evaluation
latency if an organization accumulates a very large rule set (untested at real volume yet).

**What becomes possible after**: Phase 6 can route real `REVIEW` outcomes to real human approvers.

---

## Phase 6 — Approvals

**Objective**: Implement `Approvals & Decisions`' workflow half: the `ADR-006` state machine and
`Decision` assembly from a completed `ComplianceReview`.

**Deliverables**:
- `ApprovalWorkflow` and `ApprovalRequest` entities with a DB-backed state machine (pending →
  approved/rejected/expired), allowed transitions enforced in the application layer, and an
  `AuditEvent` on every transition (`ADR-006`, `APR-001`–`APR-003`).
- `Decision` entity produced from every completed `ComplianceReview`, preserving the exact
  `PolicyVersion` used (`DEC-001`, `BR-DEC-001`).
- Manual override path: an authorized approver may override a computed status with a mandatory,
  non-empty justification, recorded as a `decision.overridden` audit event without deleting the
  original `RuleEvaluation` set (`DEC-002`, `BR-DEC-003`).
- Re-evaluation trigger: a `Decision` whose `valid_until` expires, or whose underlying
  `ContractVersion`/`PolicyVersion` changes, emits `compliance.review_required` and a new
  `Decision` is created with `supersedes_decision_id` set — never an in-place edit (`DEC-003`,
  `BR-DEC-004`).
- Celery-backed reminder/expiration tasks for pending `ApprovalRequest`s (per `ADR-006`, Celery
  triggers time-based transitions only — it never holds workflow state itself).
- Frontend approval inbox and decision-detail screens.

**Dependencies**: Phase 5 (needs a completed `ComplianceReview` to route).

**Exit criteria**: a `REVIEW` outcome correctly creates an `ApprovalRequest` routed to the
triggering rule's `approver_role`; only a user whose `Membership` role matches can resolve it
(`BR-APR-001`, verified by a cross-role test); rejecting a required step blocks `APPROVE` without an
explicit override (`BR-APR-002`); the supersedes-chain on re-evaluation is correct.

**Risks**: state-machine transition bugs under concurrent approval actions on the same request;
`BR-APR-003`'s SLA/escalation duration is a documented commercial `TBD`, so escalation timing is
untested at real volume.

**What becomes possible after**: Phase 7 can assemble a full, tamper-evident `EvidencePackage` from
a real `Decision`.

---

## Phase 7 — Evidence/Audit

**Objective**: Implement `Evidence & Audit`'s non-blockchain half: evidence packaging, the
deterministic Merkle root, and full audit-catalog coverage across everything built so far.

**Deliverables**:
- `Evidence` and `EvidencePackage` entities (`EVD-001`, `EVD-002`); deterministic Merkle-root
  computation over each package's evidence set, with a fixed canonical evidence ordering
  (`BR-EVD-001`).
- Completion of the `AuditEvent` catalog (`docs/03-domain/audit.md`) across Identity, Suppliers,
  Contracts, Policy, Compliance, and Approvals — every state-changing action to date emits an entry
  (`AUD-001`); a test confirming no update/delete path exists anywhere for `AuditEvent`, including
  for Admin roles (`AUD-002`, `BR-EVD-003`).
- Decision Passport read-model API and frontend view: decision id, supplier, contract, document
  hashes, policies evaluated (with version), rules triggered, external sources consulted, AI
  executions (model/prompt version), reviewers, final decision, timestamp — answering "why was this
  approved?" reproducibly (`docs/00-project/overview.md`).

**Dependencies**: Phase 6 (needs a real `Decision` to package).

**Exit criteria**: every `Decision` produced in Phase 6 has a corresponding `EvidencePackage` whose
`merkle_root` is recomputable and matches; the audit log demonstrably covers every state-changing
action exercised by the Phase 0–6 test suites; the Decision Passport view renders a complete,
human-readable "why" narrative for a real decision end to end.

**Risks**: Merkle-root determinism depends on a fixed canonical ordering of evidence items — a
bug here silently breaks verifiability without breaking any functional test that doesn't specifically
check recomputation; audit-log retention/volume policy is not yet addressed (deferred, not blocking).

**What becomes possible after**: Phase 8 can anchor the `EvidencePackage` hash on a real
verification layer — the last piece before the Hackathon Cut.

---

## Phase 8 — Blockchain

**Objective**: Resolve `ADR-007` via a technical spike, implement the chosen `AnchoringProvider`
adapter, build the public verification page, and freeze scope for the hackathon submission.

**Deliverables**:
- `ADR-007` spike: benchmark and implement at least one concrete `AnchoringProvider` adapter
  (`submit_hash`/`get_proof`/`verify`) against the current preferred order — (1) Constellation
  Network, (2) a generic EVM-compatible L2 testnet (Base Sepolia / Polygon Amoy) as the safest
  fallback, (3) ICP/Caffeine AI only if integration effort proves unusually low — and update
  `ADR-007`'s status to Accepted.
- `BlockchainAnchor` entity wired to `EvidencePackage`, submitting only Merkle-root hashes, never
  raw contract or personal data (`EVD-003`, `EVD-004`, `BR-EVD-002`).
- A public verification page (`docs/06-blockchain/verification.md`) letting a third party (an
  auditor, a counterparty, a hackathon judge) verify an anchored hash without logging in.
- An end-to-end demo script exercising the full pipeline: Supplier → Contract → Policy →
  Compliance → Approval → Decision → Evidence → Anchor → public Verify.
- Frontend landing page fully rewritten from the legacy legal-ERP marketing copy
  (`frontend/src/lib/landing-data.ts`) to JuriSense Gate's actual positioning (see
  `pivot-migration.md` item (d)).
- Hackathon submission materials: pitch deck, demo video, updated root `README.md`.

**Dependencies**: Phase 7 (needs a real `EvidencePackage` to anchor).

**Exit criteria** — explicitly aligned to the hackathon judging window (**2026-11-05** to
**2026-12-05**): a complete, demoable, publicly verifiable anchored `Decision` must exist and be
reachable via the public verification page **before judging opens on 2026-11-05**, and must remain
live and functioning through the close of judging on 2026-12-05. `ADR-007` is resolved to Accepted
with a working default adapter — or, if no chain integration lands in time, the documented
last-resort fallback (a hash + timestamp signed by JuriSense's own key, published to a public,
git-backed transparency log, clearly labeled as a fallback, not a blockchain anchor) is live instead,
per `risks.md`.

**Risks**: blockchain integration risk — all three candidate providers could prove too heavy for the
remaining timeline (mitigation: the fallback above, chosen specifically so the `AnchoringProvider`
abstraction never blocks the rest of the demo); scope-creep risk past this line is the reason this
Hackathon Cut exists at all.

**What becomes possible after**: the product has a real, demoable, judged, publicly verifiable MVP.
Everything below this line is committed post-hackathon product work, not required for the
submission.

---

### === HACKATHON CUT — end of Phase 8 — judging window 2026-11-05 to 2026-12-05 ===

---

## Phase 9 — Integrations

**Objective**: Build out the `Integrations` bounded context beyond the Phase 1 scaffold into real,
production-usable connectors.

**Deliverables**: outbound webhooks for `supplier.review.completed`, `contract.review.completed`,
`approval.required`, `decision.completed` (`INT-002`), with retry/backoff and signature
verification; a DocuSign e-signature integration for contract execution; a Slack notification
connector; ERP-connector groundwork for future accounts-payable/procurement-system sync.

**Dependencies**: Phase 8 complete — this phase needs stable, final domain events across every
context built through the Hackathon Cut to expose as webhooks.

**Exit criteria**: at least one real third-party integration (DocuSign or Slack) is live for a pilot
customer; webhook delivery has at-least-once semantics with idempotency keys so a customer's
downstream system is never double-notified.

**Risks**: third-party API rate limits and auth/credential-rotation complexity; webhook signature
spoofing needs its own dedicated security-audit pass before going live with a real customer.

**What becomes possible after**: customers can wire JuriSense Gate into their existing procurement
and e-signature stack instead of treating it as an isolated tool — a real adoption unblocker for
mid-market buyers.

---

## Phase 10 — Enterprise

**Objective**: Harden the platform for larger and more regulated buyers: real billing, stronger
tenant isolation, and enterprise identity.

**Deliverables**: a real payment gateway integration (Stripe or a Brazilian equivalent), resolving
`ADR-014`'s deliberately deferred payment decision; PostgreSQL Row-Level Security hardening on top
of the existing logical multi-tenancy (`ADR-003`'s documented v1.x hardening item); custom and
versioned roles beyond the seeded 10; SAML/OIDC SSO for enterprise identity providers; SLA-backed
support tiers.

**Dependencies**: Phase 9 (a working integration layer materially helps enterprise procurement
conversations); commercially gated on having real pilot customers from Phases 8–9 to justify the
investment.

**Exit criteria**: a paying enterprise customer is onboarded through the real payment gateway; RLS
is enabled on every tenant-owned table without regressing the existing RBAC/tenant-isolation test
suite; at least one SSO identity provider is verified end to end.

**Risks**: payment gateway choice carries undecided PCI-scope and Brazilian billing/tax
implications (a genuine `TBD`, not an oversight); an RLS migration on a live production database
with real customer data is a materially higher-stakes change than earlier schema work.

**What becomes possible after**: the product can be sold credibly to larger, more regulated buyers
with real billing and demonstrably stronger tenant-isolation guarantees.

---

## Phase 11 — International

**Objective**: Extend beyond Brazil via the Core Platform / Jurisdiction Pack separation the domain
model and Policy Engine were designed to support from Phase 2/4 onward.

**Deliverables**: the Jurisdiction Pack architecture formalized as a real code boundary (not just a
documented intent) separating Core Platform logic from jurisdiction-specific supplier-identity
schemes, sanctions sources, and policy rule packs; a first non-Brazil pack (US or EU, exact choice
`TBD` pending commercial priority) with its own identifier scheme, sanctions sources (e.g.
OFAC/EU-equivalent lists in place of CEIS/CNEP/CEPIM), and a GDPR-flavored policy rule pack in
place of the LGPD-flavored one; localized frontend copy for the new market.

**Dependencies**: Phase 10 (enterprise-grade multi-tenancy and billing should be solid before
multi-jurisdiction complexity is layered on top), though the domain model itself has kept
jurisdiction-specific logic swappable since Phase 2/4 by design.

**Exit criteria**: one full non-Brazil organization runs the entire Supplier → Contract → Policy →
Compliance → Decision → Evidence pipeline using its own jurisdiction pack's sources and rules, with
zero changes required to Core Platform code.

**Risks**: a genuine jurisdiction-specific legal/compliance expertise gap for each new market (local
legal counsel is a real dependency, not just an engineering task); data-residency requirements in
some jurisdictions may force per-region infrastructure the current single-VPS-plus-external-services
hosting model does not yet support.

**What becomes possible after**: JuriSense Gate becomes a genuinely multi-market platform, realizing
the long-term vision described in `docs/00-project/overview.md`.
