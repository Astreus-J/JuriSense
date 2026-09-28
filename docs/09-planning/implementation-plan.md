# Implementation Plan

A concrete, ordered sequence of implementation steps — not "build backend." This is the step-by-step
execution order underlying `roadmap.md`'s phases and `dependencies.md`'s graph; `backlog.md` breaks
each step down further into EPIC/FEATURE/STORY/TASK items that can move into Plane directly. Steps
are numbered in execution order; where two steps can genuinely run in parallel, that is called out
explicitly (see `dependencies.md` for the full reasoning).

## 1. Stabilize the repository structure for the 8-bounded-context layout

Create the `app/` package skeleton with one subpackage per bounded context — `identity`,
`suppliers`, `contracts`, `policy`, `approvals`, `evidence`, `ai_services`, `integrations` — each
pre-populated with empty `domain/`, `application/`, `infrastructure/`, and `api/` subpackages
mirroring the existing `app/accounts/` layout (`ADR-001`, `ADR-002`). Move `app/accounts/` into
`app/identity/` as part of this step (file moves only, no renames yet — renames happen in step 2, so
this step's diff is reviewable as "structure changed" independently of "names changed"). Update
`app/api/router.py` to aggregate routers from each new package under the existing `/api` prefix, and
confirm `docker compose up -d` and `uv run pytest` both still work with only import paths changed.

## 2. Rename/adapt the Identity & Organizations context from the existing Accounts code

Within `app/identity/`, mechanically rename per the full inventory in `pivot-migration.md`:
`Organizacao`→`Organization`, `Usuario`→`User`, `Perfil`→`Role` (replacing the legal-domain enum
values `administrador/advogado_senior/advogado_junior/estagiario/cliente` with the `ADR-003`
compliance values `Admin/Procurement/Legal/Compliance/Privacy/Security/Finance/Approver/Auditor/
Viewer`), `Modulo`→ the new module vocabulary (`suppliers/contracts/policies/compliance_reviews/
approvals/evidence/integrations/organization_settings`), `Plano`/`LIMITES_POR_PLANO`→ new plan
limits per `docs/02-business/pricing-strategy.md`, and `organizacao_id`→`organization_id` plus every
other Portuguese field/table/error name to English. Drop `oab`/`uf_oab` fields and the
`OabInvalidaError`/`OabJaCadastradaError` exceptions entirely — they have no meaning in a compliance
platform's user model. Regenerate the Alembic migration for the renamed schema against the external
Neon Postgres. Update every existing test to use the new names (behavior stays identical; only
identifiers change) and confirm the full existing Accounts test suite (~700 lines) still passes.
This step is deliberately a pure rename/adapt pass — no new feature logic is added here, so any
regression introduced by it is attributable to the rename itself (see `risks.md`, legacy-code
migration risk).

## 3. Establish the AuditEvent foundation

Add the `AuditEvent` entity (`id`, `event_type`, `actor_id`, `payload`, `occurred_at`, append-only,
no update/delete path anywhere including for Admin roles — `AUD-002`) and an
`emit_audit_event(event_type, actor_id, payload)` application-layer helper in a new
`app/evidence/` package (the `Evidence & Audit` context owns `AuditEvent` per
`docs/03-domain/domain-model.md`, even though the full Evidence/EvidencePackage work doesn't happen
until step 12). Wire this helper into the Identity events first — `organization.created`,
`user.registered`, `membership.invited`, `membership.accepted`, `membership.revoked` — so at least
one real code path exercises it before every later context depends on the same helper. This step is
sequenced early and deliberately ahead of its "home" phase (Phase 7) because every subsequent
context (Suppliers, Contracts, Policy, Approvals) needs to call this helper as it's built, not retrofit
it later.

## 4. Implement the Supplier domain

Build `app/suppliers/domain/` (entities: `Supplier`, `SupplierProfile`, `SupplierCheck`),
`application/` (register-supplier, trigger-check, get-profile use cases), `infrastructure/`
(repositories, ORM models with `organization_id` tenant scoping per `ADR-003`), and `api/` (CRUD
routes gated by the `suppliers` RBAC module from step 2's role/module seed). Enforce
`BR-SUP-002` (tax_id + organization_id uniqueness) at the repository layer with a real DB
constraint, not just application-layer validation. Emit `supplier.created`/`supplier.updated`/
`supplier.status_changed` via the step-3 helper.

## 5. Implement Supplier verification adapters

Build the CNPJ-registry and CEIS/CNEP/CEPIM sanctions-check adapters behind a
`SupplierVerificationPort` interface defined in `app/suppliers/domain/ports.py`, with concrete
implementations living in `app/integrations/infrastructure/` (per the `INT-001` boundary rule: the
`Integrations` context owns external-system connections; `Suppliers` only depends on the port, never
the concrete HTTP client). Wire `SupplierCheck` creation to call this port asynchronously via Celery
(per `ADR-006`, this is exactly the "short-lived background task" category, not the workflow-state
category). Normalize the raw check results into a replacing `SupplierProfile` on success
(`SUP-002`, `SUP-003`), and flag `BR-SUP-004` (a sanctions hit) as a non-silent status signal the
Supplier entity carries forward for Policy & Compliance to consume later — this step does not decide
any BLOCK/REVIEW outcome itself (`AI-004`-equivalent boundary discipline applies to Suppliers too:
no context outside Policy & Compliance decides outcomes).

*Steps 4–5 can run in parallel with steps 6–7 below — see `dependencies.md`.*

## 6. Implement Document ingestion + object storage adapter

Add s3mock to `docker-compose.yml` for local development (S3-compatible, matching production
Cloudflare R2 per `ADR-008`). Build a single `ObjectStoragePort` interface (`put`, `get`,
`generate_presigned_url`) in `app/contracts/domain/ports.py` with a s3mock/R2-compatible adapter in
`app/contracts/infrastructure/`. Build the `Document` entity and upload API: accept PDF/DOCX/TXT,
compute and persist `content_hash` (SHA-256) at upload time, never recomputed or mutated afterward.
Add basic malware/type-spoofing validation on upload per `SEC-003` before the file is persisted.

## 7. Implement the Contract/ContractVersion domain

Build `Contract` and `ContractVersion` entities: every new upload against an existing `Contract`
creates a new immutable `ContractVersion` rather than editing a prior one (`BR-CON-002`). Wire
version creation to trigger the AI extraction pipeline (step 8) asynchronously via Celery. Build the
`Clause` entity with mandatory page/span provenance back to the source `Document` (`CON-004`,
`BR-CON-004`) — a `Clause` without provenance must be rejected at the domain layer, not just flagged
in review.

## 8. Implement the AI Services extraction pipeline

Build the AI Gateway abstraction in `app/ai_services/` (`ADR-005`): a single internal interface
(`extract()`, `classify()`, `summarize()`) with pluggable OpenAI and Anthropic adapters, selected per
task type via configuration, with automatic fallback to the secondary provider on error/timeout
(`AI-003`). Every `extract()` call must use structured output (JSON schema / tool-calling) against
the schema defined in `docs/05-ai/structured-extraction.md` — never freeform text parsing — and must
return provenance metadata (document id, page, span, confidence) per field (`AI-001`, `AI-002`).
Wire the Phase 3 `ContractVersion` pipeline to call this gateway and persist the result as
`extracted_data` + `Clause` records. Implement the minimum-confidence gate (`CON-005`, `BR-CON-003`):
a `ContractVersion` below threshold is marked for mandatory human confirmation and cannot proceed to
compliance review until confirmed. Confirm the context-boundary rule holds in code, not just in
docs: `AI Services` output never directly sets any `Decision` status (`AI-004`).

## 9. Implement the Policy Engine

Run the `ADR-004` spike first, as its own timeboxed task, before writing production Policy Engine
code: benchmark `cel-python` against the five example rules in `docs/03-domain/policy-engine.md`
(`SANC-001`, `LGPD-001`, `LEGAL-008`, `FIN-003`, `FIN-004`), and decide whether the YAML `when`
clause compiles cleanly to CEL or needs the JSONLogic fallback path instead. Once the spike concludes
and `ADR-004` is updated to Accepted (or reversed), build `Policy`/`PolicyVersion`/`Rule` entities
with immutable-on-publish versioning (`BR-POL-001`, `BR-POL-002`), the YAML-to-compiled-expression
compiler, the normalized evaluation-context builder (flattening `Supplier`+`SupplierProfile`+
`SupplierCheck` and `ContractVersion.extracted_data`+`Clause` into the flat typed context
`policy-engine.md` describes), and the simulation/dry-run engine (`POL-003`) that runs a draft
`PolicyVersion` against existing contracts with zero side effects.

## 10. Implement the Compliance Engine

Build `ComplianceReview`, `RuleEvaluation`, and `Risk` entities, and the `ADR-010` aggregation
algorithm as a pure function over a set of `RuleEvaluation` outcomes: any `BLOCK` → `BLOCK`; else any
`REVIEW` → `REVIEW` (required approver = highest-severity triggered rule's `approver_role`); else
`APPROVE` (`BR-CMP-002`). Persist every `RuleEvaluation` as append-only and evidence-linked
(`BR-CMP-003`) — no update path should exist in the repository layer at all, not merely be unused.
Write the order-independence test explicitly (permute rule evaluation order, assert identical
aggregate outcome) since this is the algorithm's core safety property.

## 11. Implement the Approvals state machine

Build `ApprovalWorkflow` (routing template) and `ApprovalRequest` (concrete instance) with an
explicit DB-backed state machine (`pending`→`approved`/`rejected`/`expired`), allowed transitions
enforced in the application layer, and a step-3 `emit_audit_event()` call on every transition
(`ADR-006`). Enforce `BR-APR-001` (only a user whose `Membership.role` matches `approver_role` may
resolve a request) as a repository/application-layer check backed by a real cross-role test, not
just a UI-level restriction. Add Celery tasks for approval reminders/SLA-expiration transitions —
Celery triggers the transition, it does not hold the workflow state itself (`ADR-006`'s explicit
anti-pattern to avoid).

## 12. Implement Decision + EvidencePackage assembly

Build the `Decision` entity, produced automatically from every completed `ComplianceReview`,
preserving the exact `PolicyVersion` used (`DEC-001`, `BR-DEC-001`). Implement the manual-override
path with mandatory justification, recorded as a `decision.overridden` audit event without mutating
the original `RuleEvaluation` set (`DEC-002`, `BR-DEC-003`). Implement the re-evaluation trigger
(`DEC-003`, `BR-DEC-004`): expiring `valid_until`, or a new `PolicyVersion`/`ContractVersion`
affecting previously-used rules, emits `compliance.review_required` and produces a new `Decision`
with `supersedes_decision_id` set. Then build `Evidence`/`EvidencePackage`: assemble the complete
evidence bundle (document hashes, policy version, rule evaluations, external sources consulted, AI
executions, reviewer identities) per `EVD-001`, and compute the deterministic Merkle root over a
fixed canonical evidence ordering (`EVD-002`, `BR-EVD-001` — the ordering choice must be documented
inline in code, since a silent ordering bug breaks recomputability without breaking any test that
doesn't specifically check it).

## 13. Run the AnchoringProvider spike and implement the chosen adapter

Timebox the `ADR-007` spike explicitly: attempt the Constellation Network SDK first (best conceptual
fit, confirmed hackathon sponsor); if integration effort within the remaining timeline looks
unreasonable, fall back to a generic EVM-compatible L2 testnet (Base Sepolia or Polygon Amoy) using
viem/ethers plus a minimal hash-anchoring contract; evaluate ICP/Caffeine AI only if it shows
unusually low integration effort. Implement the `AnchoringProvider` interface
(`submit_hash(evidence_hash) -> anchor_ref`, `get_proof(anchor_ref) -> proof`,
`verify(evidence_hash, proof) -> bool`) against whichever adapter the spike selects, and wire
`BlockchainAnchor` to `EvidencePackage` — submitting only the Merkle-root hash, never raw
contract/supplier data (`EVD-003`, `EVD-004`, `BR-EVD-002`). If the spike concludes no adapter is
viable in the remaining time, implement the documented fallback instead (hash + timestamp signed by
JuriSense's own key, published to a public git-backed transparency log), explicitly labeled as a
fallback in both code comments and product copy, per `risks.md`.

## 14. Build the public verification page

Build a public (no-login) page that accepts an `EvidencePackage`/`Decision` reference or a raw hash,
calls `AnchoringProvider.get_proof()` + `verify()`, and renders a plain-language verification result
(`docs/06-blockchain/verification.md`) — this is the artifact a hackathon judge, auditor, or
counterparty actually interacts with, so it should render correctly for both the real-chain-anchor
case and the fallback-transparency-log case from step 13 without the viewer needing to know which
one is in effect beyond the explicit fallback label.

## 15. Wire the frontend app screens for the Hackathon Cut flow

Build the actual screens the demo walks through, in pipeline order: supplier registration/list/
detail (step 4), contract upload/detail with clause highlighting (steps 6–8), policy YAML
editor + simulation view (step 9), compliance review results screen surfacing WHY/EVIDENCE/POLICY/
SOURCE (step 10), approval inbox + decision detail (steps 11–12), and the Decision Passport +
public verification page (steps 12–14). Build these incrementally as each backend step lands, not
as one big frontend push at the end — each screen only needs its own backend step done, not the
whole pipeline, so this can start as early as step 4 completes.

## 16. Rewrite the frontend landing page content

Replace `frontend/src/lib/landing-data.ts` in full: the `features` array (currently 8 legal-ERP
features — case management, jurimetria, deadline alerts, etc.) becomes JuriSense Gate's actual
feature set (Supplier Intelligence, Contract Intelligence, Policy Engine, Compliance Engine,
Approvals, Evidence/Blockchain Trust Layer); the `plans` array (currently `Autônomo`/`Escritório`/
`Escritório Plus`/`Enterprise` priced for solo/small-firm lawyers) becomes the real JuriSense Gate
pricing tiers per `docs/02-business/pricing-strategy.md`; the `steps` "how it works" array, `faqs`,
and `allPlansInclude` all get rewritten to match the new product. This is 100% marketing-copy
content with no shared logic, so it can be done at any point once the pricing strategy doc exists —
it is sequenced late here only because it has zero technical dependency on anything else and should
not compete for engineering time against the Hackathon Cut's technical spikes (steps 9, 13).

## 17. Hackathon submission prep

Assemble the pitch deck, record the demo video walking the full pipeline end to end (using the same
demo scenario validated in step 10's exit criteria), update the root `README.md` to describe
JuriSense Gate rather than the archived legal-ERP product (cross-checking against
`docs/_legacy/README.md` for what NOT to carry forward), and file the actual submission before the
judging window opens on **2026-11-05**. Treat any time remaining before judging closes
(**2026-12-05**) as a stabilization/bugfix buffer for the public verification page specifically —
that page is the one artifact judges interact with directly and unsupervised, so it is the highest-
value target for last-mile polish.
