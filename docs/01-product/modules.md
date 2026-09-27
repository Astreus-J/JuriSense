# Product Modules

JuriSense Gate's product modules map 1:1 to the 8 bounded contexts defined in
`docs/03-domain/domain-model.md` and `docs/04-architecture/components.md`. Each module is a coherent
slice of the product from a user's point of view (a set of screens and capabilities), backed by
exactly one bounded context's domain model. This 1:1 mapping is intentional: it keeps the product's
information architecture and the system's internal architecture in sync, so a change in one rarely
surprises the other.

Functional requirement IDs cited below are defined in `docs/01-product/functional-requirements.md`.

---

## 1. Identity & Organizations

**What it does**: manages the tenant boundary (the `Organization` itself), user accounts, team
membership, roles/permissions, and plan limits. This is the module every other module depends on for
"who is this, what organization are they acting on behalf of, and what are they allowed to do."

**Key screens/capabilities**:
- Organization setup and settings (name, tax id, plan, billing status).
- Team management: invite users, assign roles (`Admin, Procurement, Legal, Compliance, Privacy,
  Security, Finance, Approver, Auditor, Viewer` per `ADR-003`), revoke access.
- Per-user permission overrides beyond the default role grid, for organizations that need
  finer-grained control than the seeded roles provide.
- Plan/usage view: current plan, consumption against supplier/contract/AI-execution limits.
- Multi-organization switcher for users who belong to more than one organization (e.g., a
  consultant serving multiple client companies).

**Functional requirements implemented**: `ORG-001` (organization creation), `ORG-002` (invite users
with a role), `ORG-003` (plan limit enforcement), `ORG-004` (per-user permission customization),
`ORG-005` (multi-organization membership). Also underpins `SEC-001` (tenant isolation) as the module
that owns the `organization_id` boundary every other module's data is scoped by.

---

## 2. Suppliers

**What it does**: registers third-party suppliers and runs verification checks against official/
public sources, maintaining a normalized, current profile and a full immutable check history per
supplier.

**Key screens/capabilities**:
- Supplier registry: list/search/filter suppliers by status (`prospect/under_review/approved/
  blocked/inactive`), jurisdiction, and risk indicators.
- Supplier detail view: current `SupplierProfile` (registry status, corporate structure,
  responsible parties), full `SupplierCheck` history (immutable, timestamped), and linked contracts.
- New supplier registration flow (single and bulk/CSV import).
- Manual re-check trigger, for periodic re-verification or event-driven re-checks (e.g., after news
  of a supplier's registry status change).
- Sanctions/restriction-list hit indicator, prominently surfaced wherever a supplier is referenced
  elsewhere in the product (contract review, approval queues, dashboards).

**Functional requirements implemented**: `SUP-001` (register supplier with jurisdiction-specific
identifier), `SUP-002` (trigger `SupplierCheck` on creation and manual re-check), `SUP-003`
(normalize check results into `SupplierProfile`), `SUP-004` (surface sanctions hit as blocking),
`SUP-005` (maintain full immutable check history).

---

## 3. Contracts & Documents

**What it does**: ingests contract documents, versions them, and (in partnership with AI Services)
turns them into structured, citable data — the module that owns "what does this contract actually
say."

**Key screens/capabilities**:
- Document upload (PDF/DOCX/TXT) with drag-and-drop, attached to a supplier and contract.
- Contract detail view: version history (each `ContractVersion` immutable and browsable), current
  structured extraction (parties, value, duration, liability, DPA/data-processing terms, IP,
  jurisdiction, penalties, obligations, deadlines), and clause-level citations with page/span
  highlight back into the source document.
- Low-confidence field confirmation flow: a focused review screen for fields flagged below the
  extraction confidence threshold, showing the AI's proposed value next to the cited source span for
  quick human confirm/correct.
- New-negotiation-round upload flow (creates a new `ContractVersion` against an existing `Contract`
  without ever overwriting a prior version).
- Standalone supporting-evidence upload (certificates, security attestations) not tied to a
  `ContractVersion`'s primary document.

**Functional requirements implemented**: `CON-001` (upload contract document), `CON-002` (new
`ContractVersion` per revision, never overwritten), `CON-003` (AI structured extraction on every
version), `CON-004` (page/span provenance on every clause), `CON-005` (mandatory human confirmation
for low-confidence fields). Also depends on `SEC-003` (malware/type-spoofing scan on upload).

---

## 4. Policy & Compliance

**What it does**: lets an organization author its own executable policy as versioned rules, and runs
those rules against normalized supplier + contract evidence to produce evaluated, evidence-linked
outcomes. This is the module that makes decisions the organization's own, not a black-box judgment —
the product's core differentiator (`docs/00-project/overview.md`, "Differential").

**Key screens/capabilities**:
- Policy authoring: a rule editor for the YAML DSL (`docs/03-domain/policy-engine.md`), with
  validation, syntax help, and a library of starter rule templates by category (sanctions, LGPD/
  privacy, liability, financial thresholds, security).
- `PolicyVersion` history: every published version browsable, with a clear "currently active"
  indicator and a diff view against the prior version.
- Simulation/dry-run: run a draft `PolicyVersion` against a sample of existing contracts and preview
  what would change before publishing (`POL-003`).
- Time-boxed policy exception requests, with mandatory justification and routing to the
  `approver_role` the waived rule would have required (`POL-004`).
- `ComplianceReview` detail view: every `RuleEvaluation` for a given review, with outcome, severity,
  rationale, and evidence citation, sortable/filterable by outcome and severity.
- Portfolio-level compliance dashboard: aggregate BLOCK/REVIEW/APPROVE rates, most-triggered rules,
  exception frequency — the view that turns individual reviews into a program.

**Functional requirements implemented**: `POL-001` (author policy/rules via DSL), `POL-002` (version
every published rule set immutably), `POL-003` (simulation/dry-run), `POL-004` (time-boxed
exceptions with justification), `CMP-001` (evaluate every applicable rule against normalized
evidence), `CMP-002` (aggregate per `ADR-010`), `CMP-003` (persist every `RuleEvaluation`
immutably).

---

## 5. Approvals & Decisions

**What it does**: routes `REVIEW`-outcome compliance reviews to the correct human approver(s)
through an explicit, auditable workflow, and packages the final `APPROVE/REVIEW/BLOCK` `Decision` —
the module that turns automated evaluation into an accountable human-and-machine outcome.

**Key screens/capabilities**:
- Approval queue, scoped per role: each approver sees only the `ApprovalRequest`s where their role
  is the required `approver_role`, sorted by severity/SLA urgency.
- Decision synthesis screen: a compact WHY/EVIDENCE/POLICY/RISK summary designed for a 2–5 minute
  review, with drill-down into the full contract/clause detail for anyone who wants it.
- Approve/reject action with justification field (mandatory on rejection, recommended on approval of
  anything flagged).
- Multi-step approval chain visualization (e.g., Legal → Director for `FIN-004`-tier contracts),
  showing which step is active and which have resolved.
- `Decision` detail view: final status, `valid_until`, supersede chain (if any), and — when
  applicable — override status and justification, always shown alongside the original computed
  outcome, never hiding it.
- Manual override action, gated by role, with mandatory justification (the highest-scrutiny action
  surfaced in the UI, per `docs/01-product/use-cases.md` UC-10).
- Re-evaluation/expiry indicators: contracts whose `Decision.valid_until` has expired or whose
  underlying policy/contract version changed, flagged for re-review.

**Functional requirements implemented**: `APR-001` (route REVIEW to correct approver role), `APR-002`
(role-matched resolution only), `APR-003` (multi-step chains), `DEC-001` (generate `Decision` per
completed review, preserving policy version), `DEC-002` (manual override with mandatory
justification, non-destructive), `DEC-003` (trigger re-evaluation on expiry/change).

---

## 6. Evidence & Audit

**What it does**: assembles the complete, hashable evidence bundle behind every `Decision` (the
Decision Passport) and maintains the append-only audit log of every meaningful action in the system
— the module responsible for "why was this approved, and can we trust that record."

**Key screens/capabilities**:
- Decision Passport view: one screen per `Decision` showing decision id, supplier, contract,
  document hashes, the exact `PolicyVersion` evaluated, every rule triggered, external sources
  consulted, AI executions (model/prompt version), reviewers and their resolutions, final decision,
  and timestamp — the full "why" in one place.
- Audit trail viewer: a chronological, filterable, append-only log of every `AuditEvent` for a given
  supplier, contract, or decision (and, for `Admin`/`Auditor` roles, organization-wide).
- Evidence integrity view: the `EvidencePackage`'s `Evidence` set and computed `merkle_root`, with a
  "recompute and verify" action for anyone with platform access who wants the strongest internal
  verification level.
- Export/report generation for compliance reporting and due-diligence data-room packaging.

**Functional requirements implemented**: `EVD-001` (assemble complete `EvidencePackage` per
decision), `EVD-002` (deterministic Merkle root), `EVD-004` (no raw content in on-chain payloads —
enforced at the boundary between this module and Module 8's anchoring step), `AUD-001` (append-only
audit event on every state-changing action), `AUD-002` (no update/delete operation on audit records,
including for Admin).

---

## 7. AI Services

**What it does**: provides the extraction, classification, and summarization capabilities that turn
unstructured contract documents into structured, cited data — always as an interpretation layer
feeding the Policy Engine, never as a decision-maker itself (`AI-004`).

**Key screens/capabilities**:
- Extraction result review UI (shared surface with Module 3's contract detail view): structured
  fields with confidence scores and page/span citations.
- AI execution log: which model/provider handled a given extraction, prompt version, and whether a
  fallback provider was used (`AI-003`) — primarily an internal/technical transparency surface
  referenced by the Decision Passport (Module 6) rather than a heavily-visited standalone screen.
- Confidence-threshold configuration (`Admin`-level setting): where the organization's minimum
  acceptable extraction confidence is tuned, subject to the platform-wide default and any
  jurisdiction-pack-specific calibration.

**Functional requirements implemented**: `AI-001` (extraction via AI Gateway abstraction, never
direct provider calls from other contexts), `AI-002` (confidence score and citation on every
extracted field), `AI-003` (fallback provider on error/timeout), `AI-004` (AI output never directly
sets `Decision` status — enforced architecturally, not just as a UI convention).

---

## 8. Integrations

**What it does**: connects JuriSense Gate to external systems (e-signature, messaging, future ERP/
CLM connectors) and exposes outbound webhooks for key lifecycle events, without ever granting an
external integration direct write access to business-domain tables. This module also owns the
`AnchoringProvider` connection for blockchain anchoring, conceptually — the outward-facing edge of
the platform in both directions (data in from external verification sources feeding Module 2, and
events/hashes out to external systems and the public ledger).

**Key screens/capabilities**:
- Integration configuration: connect/disconnect external systems (e.g., DocuSign, Slack), with
  credentials/config stored separately from business data.
- Webhook management: configure outbound webhook endpoints and select which lifecycle events to
  receive (`supplier.review.completed`, `contract.review.completed`, `approval.required`,
  `decision.completed`).
- Public verification page (the one unauthenticated surface in the product): hash, anchor reference,
  timestamp, and verify action for a given decision (`docs/06-blockchain/verification.md`) — see
  Module 6 for the underlying Evidence Package this surfaces, and `ADR-007` for the
  `AnchoringProvider` interface this module implements against.
- Integration activity log: connection/disconnection history and delivery status for outbound
  webhooks.

**Functional requirements implemented**: `INT-001` (configure external integration without direct
write access to business-domain tables), `INT-002` (outbound webhooks for
`supplier.review.completed`, `contract.review.completed`, `approval.required`,
`decision.completed`). Also the home of `EVD-003` (anchor the `EvidencePackage` hash via the
configured `AnchoringProvider` and expose the public verification page) in its capacity as the
module owning outward-facing connections, even though `EvidencePackage` assembly itself is owned by
Module 6 (Evidence & Audit) — anchoring is the point where Evidence & Audit's output crosses the
boundary into an external system, which is exactly what this module exists to mediate safely.

---

## Cross-module notes

- **Security (SEC) requirements** are not a separate module in the product's information
  architecture — `SEC-001` (tenant isolation), `SEC-002` (security audit gate), and `SEC-003`
  (upload malware/type-spoofing scan) are cross-cutting constraints enforced within every module
  above, not a screen a user visits. Full detail: `docs/07-engineering/security.md`.
- The 1:1 module-to-bounded-context mapping is a product/architecture alignment choice, not a
  statement that modules never share screens — several screens above (contract detail, decision
  detail) blend data from more than one module's domain model for the user's convenience, while the
  underlying write ownership remains strictly per-context (`docs/04-architecture/components.md`
  boundary rules).
