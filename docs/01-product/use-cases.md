# Use Cases

This document specifies the 12 core use cases of JuriSense Gate at implementation-ready depth. Each
use case follows the same template: Purpose, Actors, Inputs, Preconditions, Main flow, Alternative
flows, Failure cases, Outputs, Business rules, Permissions, Audit events, Security considerations,
Data created, Dependencies.

Cross-references: `BR-*` IDs are defined in `docs/03-domain/business-rules.md`; entity names are
defined in `docs/03-domain/domain-model.md`; `Role`s are defined in `ADR-003`; the aggregation
algorithm is defined in `ADR-010`; the full audit event catalog lives in `docs/03-domain/audit.md`
(referenced here by representative event names; that document is the single source of truth for the
complete list and payload shapes). Functional requirement IDs (`ORG-*/SUP-*/CON-*/POL-*/CMP-*/
APR-*/DEC-*/EVD-*/AUD-*/AI-*/SEC-*/INT-*`) are defined in `docs/01-product/functional-
requirements.md`.

---

## UC-1: Supplier Onboarding

### Purpose
Register a new third-party supplier in the system as the entry point of the entire compliance
pipeline (`docs/00-project/overview.md`'s pipeline diagram starts here), so that every subsequent
check, contract, and decision has a stable anchor to attach to.

### Actors
- **Primary**: Procurement Manager (`Procurement` role).
- **Secondary**: system (triggers the automatic `SupplierCheck` on creation, `SUP-002`).

### Inputs
- Supplier legal name.
- Jurisdiction-specific tax identifier (`tax_id` — CNPJ for the Brazil jurisdiction pack).
- Jurisdiction (defaults to the organization's home jurisdiction pack).
- Optional: internal notes, requesting department/cost center, expected contract type.

### Preconditions
- The actor has an active `Membership` in the `Organization` with the `Procurement` role (or
  `Admin`).
- The organization has not exceeded its plan's supplier limit (`BR-ORG-003`).

### Main flow
1. Procurement Manager opens "New Supplier" and enters legal name, `tax_id`, and jurisdiction.
2. System validates `tax_id` format for the selected jurisdiction pack and checks plan limits
   (`BR-ORG-003`) before allowing submission.
3. System validates uniqueness: `tax_id` + `organization_id` must not already exist (`BR-SUP-002`).
4. System creates the `Supplier` record with `status = prospect` and emits `supplier.created`.
5. System automatically triggers a `SupplierCheck` run against the jurisdiction pack's configured
   external sources (`SUP-002`) — see UC-2 for the check flow itself.
6. Supplier status transitions to `under_review` while the check runs.
7. Procurement Manager is returned to the supplier detail view, which shows `status: under_review`
   and a pending-check indicator.

### Alternative flows
- **A1 — Bulk import**: Procurement Manager uploads a CSV of multiple suppliers (name + tax_id +
  jurisdiction per row). Each row runs steps 2–6 independently; partial failures (e.g., one
  duplicate `tax_id`) do not block successful rows — the import summary reports per-row outcome.
- **A2 — Supplier already exists (soft duplicate signal)**: if the `tax_id` matches an existing
  `Supplier` in a **different** organization (not a `BR-SUP-002` violation, since uniqueness is
  scoped per organization), no special handling is required — organizations are fully isolated
  (`SEC-001`); this is noted only to clarify it is not an error condition.
- **A3 — Manual re-registration after `inactive`**: if a `tax_id` matches a `Supplier` previously
  marked `inactive` in the same organization, the system offers to reactivate the existing record
  (preserving its `SupplierCheck` history) rather than reject the creation as a duplicate.

### Failure cases
- **Invalid tax id format**: rejected client-side and server-side with a field-level error; no
  `Supplier` record created, no event emitted.
- **Duplicate `tax_id` within the organization** (`BR-SUP-002`): creation rejected with a clear
  error identifying the existing supplier record; no new record created.
- **Plan limit exceeded** (`BR-ORG-003`): creation rejected with a `402`-style plan-limit error
  (mirrors the existing `LimiteUsuariosAtingidoError` pattern); existing data is never deleted or
  degraded as a side effect.
- **Actor lacks permission**: rejected with an authorization error; no record created, and the
  attempt itself is still audited as a denied-access event for security monitoring purposes.

### Outputs
- A new `Supplier` record with `status = prospect` transitioning to `under_review`.
- A triggered `SupplierCheck` (see UC-2) running asynchronously.
- Confirmation UI state and, per `INT-002`, an available webhook hook point for downstream systems
  once the check later completes.

### Business rules
- `BR-SUP-001`: the `Supplier` belongs to exactly one `Organization`.
- `BR-SUP-002`: `tax_id` + `organization_id` uniqueness.
- `BR-ORG-003`: plan limits enforced at creation, non-retroactive.

### Permissions
- Create: `Procurement`, `Admin`.
- View: `Procurement`, `Legal`, `Compliance`, `Privacy`, `Security`, `Finance`, `Approver`,
  `Auditor` (read-only), `Admin`. `Viewer` has read access per its default grant.

### Audit events
- `supplier.created` (full catalog and payload shape in `docs/03-domain/audit.md`).

### Security considerations
- Tenant isolation enforced via `organization_id` at the repository layer (`SEC-001`, `ADR-003`);
  every query for supplier lookup/uniqueness must be scoped to the acting organization to prevent
  cross-tenant leakage of another company's supplier registry.
- Input validation on `tax_id` and free-text fields to prevent injection into downstream external
  source queries (UC-2 uses this data to query official sources).
- Denied-access attempts are logged for security monitoring, not silently dropped.

### Data created
- `Supplier` (`docs/03-domain/domain-model.md`).

### Dependencies
- UC-2 (Supplier Verification/Check) is triggered automatically as part of this use case's main
  flow.
- `Organization` and `Membership` (Identity & Organizations context) must already exist.

---

## UC-2: Supplier Verification / Check

### Purpose
Produce a point-in-time, evidence-backed verification of a supplier's registry and compliance
status against official/external sources, forming the factual foundation the Policy Engine later
evaluates (`docs/00-project/overview.md`, "Supplier Intelligence").

### Actors
- **Primary**: system (automatic trigger from UC-1, or scheduled re-check).
- **Secondary**: Procurement Manager or Compliance Officer (manual re-check request).

### Inputs
- `Supplier` record (`tax_id`, jurisdiction).
- Jurisdiction pack's configured source adapters (for Brazil: company registry status, CEIS/CNEP/
  CEPIM sanctions/restriction lists, corporate structure — `docs/00-project/overview.md`).

### Preconditions
- A `Supplier` record exists.
- At least one source adapter is configured and reachable for the supplier's jurisdiction.

### Main flow
1. System creates a `SupplierCheck` record with `status = started`, `started_at = now`, and emits
   `supplier.check.started`.
2. System queries each configured external source for the jurisdiction pack, recording
   `sources_consulted` and `raw_results` per source.
3. System evaluates whether any source returned a positive sanctions/restriction-list hit.
4. System normalizes the raw results into an updated `SupplierProfile` (registry status, corporate
   structure, responsible parties, CNAE/jurisdiction equivalent, address) — replacing, not mutating,
   any previous profile (`SupplierProfile`'s lifecycle is "replaced on every successful re-check").
5. System marks the `SupplierCheck` `status = completed`, sets `completed_at`, and emits
   `supplier.check.completed` and `supplier.profile_updated`.
6. If a sanctions hit was found, the `Supplier` is flagged toward the `BLOCK` path via rule
   `SANC-001` at the next `ComplianceReview` (`BR-SUP-004`) — this use case does not itself decide
   `Supplier.status`; that transition happens through the compliance review pipeline (UC-6/UC-7).
7. If no blocking condition and the check is the qualifying check for approval, the `Supplier` may
   move from `under_review` toward `approved` once other pipeline stages (contract review, if
   applicable) also clear — see `BR-SUP-003`.

### Alternative flows
- **A1 — Manual re-check request**: a Compliance Officer or Procurement Manager requests a re-check
  on an existing supplier (e.g., annual re-verification, or after a news event). Flow proceeds
  identically from step 1, producing a new immutable `SupplierCheck` record alongside — never
  replacing — prior checks (`SUP-005`).
- **A2 — Scheduled periodic re-check**: system-initiated on a configured cadence (exact cadence is a
  `TBD`, see NFR doc), identical flow to A1 but actor is the scheduler rather than a person.
- **A3 — Partial source failure**: one configured source is unreachable/times out while others
  succeed. The check completes using the available sources, and the unreachable source is recorded
  in `sources_consulted` with a failure status rather than silently omitted — this partial-coverage
  state is itself visible to the reviewer (see Failure cases).

### Failure cases
- **All sources unreachable**: `SupplierCheck.status = failed`; no `SupplierProfile` update occurs;
  the prior `SupplierProfile` (if any) remains the current one; an alert is raised for manual
  follow-up since the supplier cannot proceed through the pipeline without a completed check
  (`BR-SUP-003`).
- **Malformed/ambiguous source response** (e.g., multiple registry entries match the same `tax_id`
  due to a name collision in the source data): check completes with an `ambiguous` sub-status
  requiring manual disambiguation by Procurement or Compliance before the profile is finalized —
  this is treated as a data-quality failure mode, not silently resolved by picking the first match.
- **Sanctions hit found**: not a "failure" of the check itself (the check succeeded at its job of
  detecting the condition) — see main flow step 6; this is the expected, correctly-functioning
  detection path.

### Outputs
- An immutable `SupplierCheck` record (`SUP-005`: full history retained, never overwritten).
- An updated `SupplierProfile` reflecting the latest successful check (`SUP-003`).
- A sanctions-hit flag available as normalized evaluation-context input (`supplier.sanctions_hit`)
  for the Policy Engine (`docs/03-domain/policy-engine.md`).

### Business rules
- `BR-SUP-003`: a `Supplier` cannot move to `approved` without a `completed` `SupplierCheck` newer
  than any open sanctions flag.
- `BR-SUP-004`: a positive sanctions hit forces the `BLOCK` path via `SANC-001`; it cannot be
  silently ignored, and any override requires an explicit exception record.

### Permissions
- Trigger manual re-check: `Procurement`, `Compliance`, `Admin`.
- View check results/history: `Procurement`, `Legal`, `Compliance`, `Privacy`, `Security`,
  `Finance`, `Approver`, `Auditor`, `Admin`.

### Audit events
- `supplier.check.started`, `supplier.check.completed`, `supplier.profile_updated`.

### Security considerations
- External source queries must not leak the supplier's data to unintended third parties beyond the
  legitimate lookup — source adapters are scoped, credentialed integrations, not ad hoc scraping,
  and must not embed customer-identifying context (e.g., the organization's own name) in a way that
  exposes which company is investigating which supplier to the source provider beyond what the
  lookup itself requires.
- `raw_results` may contain personal data of a supplier's responsible parties (e.g., a company
  officer's name in a registry record) — handled under the same LGPD posture as the rest of the
  platform (`docs/06-blockchain/privacy.md`'s neighboring principle applies here too: normalized
  data, not raw dumps, flows downstream into evidence).
- Immutability of `SupplierCheck` once `completed` (`domain-model.md` invariant) prevents retroactive
  tampering with what a supplier's status was known to be at a point in time — this is foundational
  to the audit trail's credibility.

### Data created
- `SupplierCheck`, `SupplierProfile` (replaced).

### Dependencies
- Requires `Supplier` (UC-1) to exist.
- Feeds evaluation context for UC-6 (Compliance Review) and UC-7 (Risk Classification).
- Jurisdiction pack source adapters (`docs/00-project/overview.md`, "Internationalization") must be
  configured per `Organization`'s jurisdiction.

---

## UC-3: Contract Ingestion

### Purpose
Bring a contract document into the system as a new, immutable, versioned artifact, establishing the
`Contract`/`ContractVersion`/`Document` chain that every later extraction, review, and decision
attaches to.

### Actors
- **Primary**: Procurement Manager or Legal Counsel.
- **Secondary**: system (malware/type scan, hash computation, version creation).

### Inputs
- Contract file (PDF, DOCX, or TXT).
- Associated `Supplier` (existing or created inline as part of the same flow).
- Contract metadata: title, contract type (e.g., MSA, SaaS subscription, NDA, SOW).

### Preconditions
- Actor has `Procurement` or `Legal` role (or `Admin`).
- The associated `Supplier` exists (or is created in the same transaction — UC-1).
- Organization has not exceeded its plan's contract-review limit (`BR-ORG-003`).

### Main flow
1. Actor uploads the contract file and selects/creates the associated `Supplier`.
2. System validates and scans the uploaded file for malware and type-spoofing (`SEC-003`) before any
   further processing.
3. System computes `content_hash` (SHA-256) over the file and stores it via the configured object
   storage backend (`ADR-008`), creating a `Document` record with `status = uploaded`.
4. If no existing `Contract` for this supplier/title context is selected, system creates a new
   `Contract` with `status = draft` and emits `contract.created`.
5. System creates a new `ContractVersion` referencing this `Document`, with `version_number`
   incremented from any prior version of the same `Contract` (`BR-CON-002`: never edits an existing
   version), and emits `document.uploaded` and `contract.version_created`.
6. System marks the `Document` `status = processed` once initial validation completes and hands the
   `ContractVersion` off to AI structured extraction (UC-4) automatically.
7. Actor is shown the contract detail view with `status: under_review` and an in-progress extraction
   indicator.

### Alternative flows
- **A1 — New negotiation round on an existing contract**: actor uploads a revised document against
  an existing `Contract`. System creates a new `Document` and a new `ContractVersion` with an
  incremented `version_number` (`BR-CON-002`); the prior `ContractVersion` is preserved, unedited,
  and remains queryable as history.
- **A2 — Supporting evidence upload (not the primary contract)**: actor uploads a supporting
  document (e.g., a vendor's security certificate) that is not itself the contract. System creates a
  standalone `Document` not attached to a `ContractVersion` as its source file, but referenceable as
  `Evidence` later (UC-11).
- **A3 — Unsupported or corrupted file**: see Failure cases.

### Failure cases
- **Malware/type-spoofing detected** (`SEC-003`): upload rejected outright; no `Document` record
  created; a security-relevant audit event is still recorded (the attempt, not the content).
- **Unsupported file type or corrupted file**: rejected with a clear error before hash computation;
  no partial `Document` record left in an inconsistent state.
- **Plan limit exceeded** (`BR-ORG-003`): rejected with a plan-limit error; no record created.
- **Storage backend failure**: upload fails atomically — no `Document` row is created without a
  corresponding successfully-stored object; this is a data-consistency invariant the application
  layer enforces, not a best-effort behavior.

### Outputs
- A `Document` record with computed `content_hash`.
- A `Contract` (new or existing) and a new `ContractVersion` in `extracted`-pending state, handed to
  UC-4.

### Business rules
- `BR-CON-001`: a `Contract` belongs to exactly one `Supplier`.
- `BR-CON-002`: every negotiation round creates a new `ContractVersion`; no in-place edits.
- Document immutability invariant: `content_hash` computed once, never recomputed/mutated
  (`domain-model.md`).

### Permissions
- Upload/create: `Procurement`, `Legal`, `Admin`.
- View: `Procurement`, `Legal`, `Compliance`, `Privacy`, `Security`, `Finance`, `Approver`,
  `Auditor`, `Admin`.

### Audit events
- `document.uploaded`, `contract.created` (first version only), `contract.version_created`.

### Security considerations
- `SEC-003` malware/type-spoofing scan is mandatory and blocking — no path exists to skip it, even
  for trusted-looking uploaders, since a compromised account is exactly the scenario this control
  defends against.
- Tenant isolation (`SEC-001`) on `Document`/`Contract`/`ContractVersion` storage and retrieval.
- Object storage keys must not be predictable/enumerable across tenants (`ADR-008`).
- The immutable `content_hash` is the anchor for later evidence integrity (UC-11/UC-12) — any defect
  in hash computation correctness undermines the entire evidence chain downstream, so this step
  carries outsized security importance relative to its apparent simplicity.

### Data created
- `Document`, `Contract` (if new), `ContractVersion`.

### Dependencies
- Requires `Supplier` (UC-1).
- Triggers UC-4 (AI Extraction) automatically.
- Depends on the object storage backend (`ADR-008`) and malware-scanning capability (`SEC-003`,
  `docs/07-engineering/security.md`).

---

## UC-4: AI Extraction

### Purpose
Convert an unstructured contract document into structured, citable, machine-evaluable data — the
critical translation step between "a PDF" and "something the Policy Engine can reason about."

### Actors
- **Primary**: system (`AI Services` bounded context, via the AI Gateway abstraction).
- **Secondary**: Legal Counsel or Privacy/Security Lead (manual confirmation of low-confidence
  fields).

### Inputs
- `ContractVersion.document_id` (the source `Document`).
- The structured extraction schema (`docs/05-ai/structured-extraction.md`).

### Preconditions
- `ContractVersion` exists with `status` pending extraction (from UC-3).
- AI Gateway is reachable (primary provider, with fallback configured per `ADR-005`).

### Main flow
1. System submits the source document to the AI Gateway's `extract()` interface (`ADR-005`),
   requesting structured output only (JSON schema/tool-calling — never freeform text parsing,
   `AI-001`).
2. AI Gateway returns structured fields: parties, value/currency, duration, renewal/termination
   terms, liability type and caps, confidentiality terms, IP terms, DPA presence and
   personal-data-processing indicators, jurisdiction, guarantees, penalties, obligations, and
   deadlines — each field carrying a confidence score and a source citation (document/page/span,
   `AI-002`).
3. System persists this as `ContractVersion.extracted_data` (JSON) and `extraction_confidence`.
4. For every clause-shaped extraction (liability, DPA, termination, etc.), system creates a `Clause`
   record with `clause_type`, `page`, `text_span`, and `confidence`, each carrying mandatory
   page/span provenance back to the source `Document` (`CON-004`, `BR-CON-004` — a clause without
   provenance cannot be used as evidence in a `RuleEvaluation`).
5. System checks whether every field meets the minimum extraction confidence threshold
   (`BR-CON-003`, threshold value itself a documented `TBD` pending calibration — see
   `docs/05-ai/evaluation.md`).
6. If all fields clear the threshold, `ContractVersion.status` moves to `analyzed` and system emits
   `contract.analysis_completed`, automatically triggering UC-5 (Policy Execution).
7. If any field falls below threshold, the `ContractVersion` is flagged for mandatory human
   confirmation (`CON-005`) before proceeding — see Alternative flow A1.

### Alternative flows
- **A1 — Low-confidence field requires human confirmation** (`BR-CON-003`, `CON-005`): a
  Legal/Privacy/Security user reviews the flagged field against the cited page/span in the source
  document and either confirms the AI's extracted value or corrects it manually. Once every
  low-confidence field is confirmed, `ContractVersion.status` moves to `analyzed` and the pipeline
  proceeds to UC-5. The manual correction is itself recorded as part of the extraction record (not a
  silent overwrite) so the Decision Passport can later show which fields were AI-extracted
  as-is versus human-confirmed/corrected.
- **A2 — Primary AI provider failure/timeout** (`AI-003`): AI Gateway automatically falls back to
  the configured secondary provider; the extraction proceeds transparently to the rest of the flow.
  Which provider actually produced a given extraction is recorded as part of provenance metadata.
- **A3 — Re-extraction on a new `ContractVersion`**: each new negotiation round (UC-3, A1) triggers
  this use case fresh against the new version; prior versions' extractions remain immutable and
  untouched.

### Failure cases
- **Both primary and secondary AI providers fail**: extraction job fails; `ContractVersion` remains
  in a pending state; the failure is surfaced to the uploader with a retry option; no partial/
  corrupted `extracted_data` is persisted (all-or-nothing per field-set commit).
- **AI output fails schema validation** (i.e., the provider returns malformed structured output):
  treated identically to a provider failure — rejected, not coerced or guessed into shape, since
  `AI-001` requires structured output the system can trust the shape of.
- **Document is unreadable/unparseable** (e.g., a scanned image PDF with no extractable text and no
  OCR configured yet): extraction fails with a specific "document not machine-readable" error
  distinct from a provider outage, prompting the uploader toward a text-layer/OCR remediation path
  (OCR pipeline detail: `docs/05-ai/document-intelligence.md`).

### Outputs
- `ContractVersion.extracted_data` and `extraction_confidence`.
- A set of `Clause` records with provenance.
- `ContractVersion.status = analyzed` once confidence/confirmation requirements are satisfied.

### Business rules
- `BR-CON-003`: minimum confidence threshold or human confirmation required before `analyzed`.
- `BR-CON-004`: every `Clause` must carry page/span citation to be usable as evidence.

### Permissions
- Trigger: automatic (system), no direct user action to invoke.
- Confirm/correct low-confidence fields: `Legal`, `Privacy`, `Security`, `Compliance`, `Admin`
  (role depends on which field category is flagged — a DPA-presence flag should reasonably route to
  `Privacy`, a liability-type flag to `Legal`).
- View extracted data and clauses: same broad view set as UC-3.

### Audit events
- `contract.analysis_completed`. (Manual confirmation/correction of a low-confidence field is its
  own catalogued event in `docs/03-domain/audit.md`.)

### Security considerations
- `AI-001`/`AI-004`: AI Services output is never allowed to directly set a `Decision` status — this
  is a hard architectural boundary enforced at the context-integration layer, not a convention, and
  exists specifically so that a prompt-injection attempt embedded in a malicious contract document
  (e.g., text designed to manipulate an LLM into asserting favorable terms) cannot, even in
  principle, produce an automatic approval; it can only ever produce structured facts that the
  Policy Engine (UC-5) independently evaluates against the customer's own rules.
  See `docs/05-ai/ai-strategy.md` and `docs/05-ai/document-intelligence.md` for the prompt-injection
  and adversarial-document threat model in full.
- Document content sent to third-party AI providers is subject to the same LGPD data-processing
  posture as the rest of the platform (`docs/06-blockchain/privacy.md`'s neighboring principles;
  full AI-specific data handling in `docs/05-ai/ai-strategy.md`) — provider data-retention/training-
  opt-out terms are a contractual prerequisite for any provider onboarded into the AI Gateway.
- Confidence scores and provenance are never discarded even when a human later corrects a value —
  the original AI output remains visible in the record for auditability of the correction itself.

### Data created
- `ContractVersion.extracted_data` (field update), `Clause` (multiple).

### Dependencies
- Requires `ContractVersion`/`Document` (UC-3).
- Depends on the AI Gateway abstraction (`ADR-005`) and structured extraction schema
  (`docs/05-ai/structured-extraction.md`).
- Triggers UC-5 (Policy Execution) automatically once `analyzed`.

---

## UC-5: Policy Execution

### Purpose
Run the organization's own executable policy rules against normalized supplier and contract
evidence, producing an individual, evidence-linked outcome for each applicable rule — the mechanical
core that makes decisions reproducible and explainable.

### Actors
- **Primary**: system (`Policy & Compliance` bounded context).

### Inputs
- The `ContractVersion.extracted_data` and `Clause` list (from UC-4).
- The `Supplier`, current `SupplierProfile`, and latest `SupplierCheck` (from UC-2).
- The organization's current (published) `PolicyVersion` and its `Rule` set.

### Preconditions
- `ContractVersion.status = analyzed` (UC-4 complete).
- The `Supplier` has at least one `completed` `SupplierCheck` (UC-2 complete).
- The organization has a published `PolicyVersion` (`BR-POL-002`: exactly one current version).

### Main flow
1. System creates a `ComplianceReview` with `status = started`, referencing the `ContractVersion`
   and the current `PolicyVersion`, and emits `compliance.review_started`.
2. `Policy & Compliance`'s application layer builds a single **normalized evaluation context** from
   `Supplier` + `SupplierProfile` + latest `SupplierCheck` and `ContractVersion.extracted_data` +
   `Clause` list — a flat, typed object (e.g. `supplier.sanctions_hit`, `contract.liability.type`,
   `contract.value.brl`, `contract.processes_personal_data`, `contract.dpa_present`) per
   `docs/03-domain/policy-engine.md`, "Evaluation context & input normalization." Rules never touch
   raw AI output or raw documents directly (`BR-CMP-001`).
3. System evaluates every `Rule` in the current `PolicyVersion` against this context, independent of
   rule order (`docs/03-domain/policy-engine.md`, "Rule priority & conflicting rules").
4. For each rule, system produces a `RuleEvaluation` record with `outcome ∈ {PASS, REVIEW, BLOCK,
   NOT_APPLICABLE}`, `severity`, `evidence_refs` (pointing to the specific `Clause`/`SupplierCheck`
   that triggered or satisfied the rule), and a human-readable `rationale`, and emits
   `compliance.rule_evaluated` for each (`CMP-001`, `CMP-003`).
5. System marks `ComplianceReview.status = completed`, sets `completed_at`, and emits
   `compliance.review_completed`.
6. Control passes to UC-6 (Compliance Review, in the sense of the human-facing review/reading of
   these results) and UC-7 (Risk Classification), which consume this `ComplianceReview`'s
   `RuleEvaluation` set to produce the `Decision` (UC-9).

### Alternative flows
- **A1 — Policy simulation/dry-run** (`POL-003`): a Legal/Compliance user runs a **draft**
  `PolicyVersion` against a sample of existing `ContractVersion`s. This follows the same evaluation
  logic (steps 2–4) but does **not** create a real `ComplianceReview`/`Decision`/audit event trail —
  it is explicitly a non-committing simulation (`docs/03-domain/policy-engine.md`, "Simulation /
  dry-run"), used to answer "if we tighten this rule, how many active contracts would suddenly
  fail?" before publishing.
- **A2 — Re-evaluation trigger** (`BR-DEC-004`): a `Decision`'s `valid_until` expiring, or a newly
  published `PolicyVersion` affecting previously-evaluated rules, or a new `ContractVersion` being
  ingested for the same `Contract`, triggers `compliance.review_required`, which re-runs this use
  case from step 1 against the current state, producing a new `ComplianceReview`/`Decision` (never
  editing the prior one — `BR-DEC-002`).
- **A3 — Time-boxed policy exception applied** (`POL-004`): if an active, approved exception exists
  for a specific rule/supplier/contract combination, the rule still evaluates and still produces a
  `RuleEvaluation` (never silently skipped), but its outcome is annotated as exception-covered; the
  exception itself is a separate, audited record with mandatory justification and the same
  `approver_role` sign-off the waived rule would have required (`docs/03-domain/policy-engine.md`,
  "Exceptions & manual overrides").

### Failure cases
- **No published `PolicyVersion` exists for the organization**: the `ComplianceReview` cannot start;
  the organization is prompted to author and publish at least a baseline policy before contracts can
  be reviewed — this is treated as a configuration gap, not a silent pass-through approval.
- **Evaluation context cannot be fully normalized** (e.g., a required extracted field is missing
  because the `ContractVersion` was force-advanced past confidence checks incorrectly — should not
  happen given `BR-CON-003`, but is defended against): rules that depend on the missing field
  evaluate to a defined `NOT_APPLICABLE` rather than silently `PASS`ing, so a data gap can never
  masquerade as a clean bill of health.
- **Rule compilation error in a published `PolicyVersion`** (should be caught at publish time, but
  defended against here too): the affected rule is marked as `failed` at evaluation, surfaced
  prominently to Legal/Compliance, and does **not** silently resolve to `PASS` — a broken rule fails
  loud, never quiet, consistent with "BLOCK is the safer failure mode" philosophy underlying `ADR-
  010`.

### Outputs
- A completed `ComplianceReview` with a full set of immutable `RuleEvaluation` records.

### Business rules
- `BR-CMP-001`: evaluation always uses normalized evidence, never raw AI output.
- `BR-CMP-002`: aggregation order-independence (elaborated fully in UC-6/UC-9).
- `BR-CMP-003`: `RuleEvaluation` is append-only, never edited or deleted.
- `BR-POL-001`, `BR-POL-002`: policy/rule versioning and single-current-version invariants.

### Permissions
- Trigger: automatic (system) for the main pipeline; `Legal`/`Compliance`/`Admin` for manual
  simulation (`POL-003`) and manual re-evaluation requests.
- View: broad read access identical to UC-3/UC-4 view set.

### Audit events
- `compliance.review_started`, `compliance.rule_evaluated` (per rule), `compliance.review_completed`,
  `compliance.review_required` (on re-trigger).

### Security considerations
- Evaluation context construction is the trust boundary between `AI Services`' raw output and the
  deterministic Policy Engine — a bug here that let raw AI text leak into rule conditions (instead
  of normalized typed fields) would reintroduce exactly the AI-can't-decide-outcomes risk `AI-004`
  is designed to prevent; this boundary is a first-class thing to test, not an implementation detail.
- Rule evaluation must be deterministic and side-effect-free with respect to anything outside the
  `ComplianceReview`/`RuleEvaluation` records it creates — no rule should be able to, say, directly
  mutate a `Supplier.status` as a side effect, since state transitions belong to their owning
  aggregate's own lifecycle rules, not to rule-evaluation code.

### Data created
- `ComplianceReview`, `RuleEvaluation` (multiple, one per applicable rule).

### Dependencies
- Requires `ContractVersion` in `analyzed` state (UC-4) and `Supplier` with a `completed`
  `SupplierCheck` (UC-2).
- Requires an existing published `PolicyVersion` (authored via the policy-authoring flow described
  in `docs/03-domain/policy-engine.md`, itself out of scope as a numbered use case here since it is
  configuration rather than the operational pipeline).
- Feeds UC-6, UC-7, and UC-9.

---

## UC-6: Compliance Review

### Purpose
Give a Compliance Officer (and other relevant roles) a coherent, human-readable reading of a
`ComplianceReview`'s results — surfacing WHY/EVIDENCE/SOURCE per triggered rule — so that a person
can understand, investigate, and act on what the Policy Engine found, before or alongside the formal
`Decision` and any required approval.

### Actors
- **Primary**: Compliance Officer.
- **Secondary**: Legal Counsel, Privacy Officer, Security Lead (each reviewing their own
  rule-category findings).

### Inputs
- A completed `ComplianceReview` (from UC-5) with its `RuleEvaluation` set.

### Preconditions
- `ComplianceReview.status = completed`.

### Main flow
1. Compliance Officer opens the `ComplianceReview` detail view for a given `ContractVersion`.
2. System presents every `RuleEvaluation`, grouped/sortable by outcome (`BLOCK` first, then
   `REVIEW`, then `PASS`/`NOT_APPLICABLE`) and by severity within each group.
3. For each triggered (non-`PASS`) rule, the Compliance Officer inspects the `rationale` and
   `evidence_refs`, which link directly to the specific `Clause` (with page/span highlight in the
   source document) or `SupplierCheck` result that caused the outcome.
4. Compliance Officer determines whether the finding is a genuine issue requiring action or, on
   inspection, warrants a documented policy exception (`POL-004`, see UC-5 A3) — this determination
   is recorded, not silent.
5. If the review surfaces a pattern worth escalating (e.g., recurring `REVIEW` triggers on the same
   rule across many suppliers), Compliance Officer can flag it for policy review (feeding back into
   policy authoring, outside this use case's scope).
6. Compliance Officer's investigation does not itself change the `Decision` outcome (that remains
   the deterministic aggregation from UC-9) unless they proceed to request a manual override
   (UC-10) or grant an exception (UC-5 A3) through the explicit, audited mechanisms provided for
   that.

### Alternative flows
- **A1 — Cross-functional review**: Legal, Privacy, and Security each review only the subset of
  `RuleEvaluation`s tagged to their rule category (their filtered queue, per `docs/01-product/
  personas.md`), rather than the Compliance Officer reviewing everything alone — this is the normal
  mode for any review touching multiple rule categories simultaneously.
- **A2 — Portfolio-level review**: instead of a single `ComplianceReview`, Compliance Officer views
  an aggregate dashboard across many suppliers/contracts (BLOCK/REVIEW/APPROVE rates, most-triggered
  rules, exception frequency) to identify systemic issues rather than one-off ones.

### Failure cases
- **Reviewer lacks context for a citation** (e.g., the linked `Clause` text_span is ambiguous
  without surrounding context): UI is expected to render enough surrounding document context around
  the cited span to be self-explanatory; a citation that requires opening and manually searching the
  full document defeats the purpose of `CON-004`'s provenance requirement, so this is treated as a
  product-quality bar, not merely a nice-to-have.
- **Reviewer attempts to edit a `RuleEvaluation` directly**: not possible by design (`BR-CMP-003`:
  append-only); the UI does not expose an edit affordance at all — only the exception (UC-5 A3) and
  override (UC-10) mechanisms exist, and both create new, separate audited records.

### Outputs
- A reviewed, human-understood `ComplianceReview` state (no new entity by itself — this use case is
  primarily an information/investigation flow that feeds UC-7, UC-8, UC-9, UC-10 decisions).
- Optionally, a policy exception request (UC-5 A3) or a flag for future policy revision.

### Business rules
- `BR-CMP-003`: append-only `RuleEvaluation` — reviewers can annotate/act but never edit history.

### Permissions
- View: `Compliance` (primary), `Legal`, `Privacy`, `Security`, `Finance` (each scoped to their rule
  category or full view depending on org configuration), `Auditor` (full read), `Admin`.
- Initiate exception request: `Compliance`, `Legal` (role matching the rule's `approver_role`).

### Audit events
- No new event type beyond what UC-5 already emitted for the review itself; if an exception request
  is initiated from this flow, that is UC-5 A3's audited exception-request event.

### Security considerations
- Read access to `RuleEvaluation` evidence must respect the same tenant isolation as everything else
  (`SEC-001`) — a Compliance Officer at Organization A must never be able to view Organization B's
  reviews, including via any cross-org reporting/analytics feature.
- Evidence citations that link to source `Document` content must enforce the same access-control
  check as direct document access — a link should not become an access-control bypass.

### Data created
- None directly (investigation/read use case); may lead to UC-5 A3 (exception) or UC-10 (override)
  data creation.

### Dependencies
- Requires a completed `ComplianceReview` (UC-5).
- Feeds UC-7 (Risk Classification), UC-8 (Approval Routing), UC-9 (Decision Generation), and
  optionally UC-10 (Manual Override).

---

## UC-7: Risk Classification

### Purpose
Surface and prioritize risk findings from a `ComplianceReview` — including informational/
non-blocking findings that may not map 1:1 to a specific rule outcome — so reviewers and approvers
can triage by severity rather than treating every finding as equally urgent.

### Actors
- **Primary**: system (produces `Risk` records as part of/alongside `ComplianceReview`).
- **Secondary**: Compliance Officer, Approver (consume the prioritized view).

### Inputs
- The `ComplianceReview`'s `RuleEvaluation` set (UC-5).
- Any additional AI-surfaced findings that are informational rather than rule-triggering (e.g., a
  clause that is unusual but does not violate any configured rule — still worth a human's attention).

### Preconditions
- `ComplianceReview.status = completed`.

### Main flow
1. For each `RuleEvaluation` with a non-`PASS`/`NOT_APPLICABLE` outcome, system creates or links a
   corresponding `Risk` record with `category`, `description`, `severity`, and `evidence_refs`.
2. System also allows `Risk` records that do not map 1:1 to a `RuleEvaluation` — for
   informational findings the AI extraction surfaced as notable but that no configured rule
   currently governs (e.g., an unusual indemnification structure that isn't yet covered by a
   specific policy rule) — so that "no rule fired" and "verified clean" remain distinguishable in
   the record from "nothing was even looked at."
3. System ranks all `Risk` records by `severity` (`critical/high/medium/low`) for the reviewer's
   worklist, per `docs/03-domain/policy-engine.md`, "Severity & escalation" — severity affects
   prioritization and which `approver_role` is required when multiple `REVIEW` rules fire
   (highest-severity wins), but never changes the `APPROVE/REVIEW/BLOCK` aggregation itself.
4. Compliance Officer/Approver consumes this ranked view when deciding what to look at first,
   especially under time pressure with many open reviews.

### Alternative flows
- **A1 — Portfolio-level risk view**: risk findings aggregated across all active suppliers/
  contracts, letting Compliance identify which risk categories recur most often company-wide (useful
  input to policy tightening decisions, not itself a policy change).

### Failure cases
- **Severity misclassification by a rule author** (e.g., a rule that should be `critical` was
  authored as `low`): this is a policy-authoring quality issue, not a system defect — the Risk
  Classification use case faithfully reflects whatever severity the current `PolicyVersion`'s rule
  declares; correcting it requires publishing a new `PolicyVersion` (`BR-POL-001`), not a
  runtime override of an individual `Risk` record's severity.

### Outputs
- A set of `Risk` records, ranked, associated with the `ComplianceReview`.

### Business rules
- Severity does not change aggregation outcome (documented in `docs/03-domain/policy-engine.md`,
  reiterated here since it is a common point of confusion: a `low`-severity `REVIEW` rule still
  forces `REVIEW`, it only sorts lower in a worklist).

### Permissions
- View: same broad set as UC-6.
- No create/edit UI for `Risk` beyond what the system produces from `RuleEvaluation`/extraction —
  this is a derived, not directly authored, entity.

### Audit events
- No independent event type (covered by `compliance.rule_evaluated`/review completion, per
  `domain-model.md`'s `Risk` entity definition).

### Security considerations
- Same tenant-isolation and evidence-access considerations as UC-6.

### Data created
- `Risk` (multiple, immutable once created).

### Dependencies
- Requires a completed `ComplianceReview` (UC-5).
- Feeds UC-8 (Approval Routing, via severity-driven approver selection) and UC-9 (Decision
  Generation).

---

## UC-8: Approval Routing / Resolution

### Purpose
Route a `REVIEW`-outcome `ComplianceReview` to the correct human approver(s) through an explicit,
auditable state machine, and record their resolution — the mechanism that turns "the machine can't
auto-approve this" into a real, accountable human decision.

### Actors
- **Primary**: system (routes the request per the configured `ApprovalWorkflow`).
- **Secondary**: the named approver (Legal, Compliance, Privacy, Security, Finance, or Approver/
  Director depending on the triggered rule's `approver_role` and severity).

### Inputs
- A `ComplianceReview` whose aggregated preliminary outcome (per UC-9's algorithm, computed ahead of
  or alongside routing) is `REVIEW`.
- The organization's configured `ApprovalWorkflow` (trigger condition → ordered approver-role steps,
  `ADR-006`).

### Preconditions
- `ComplianceReview.status = completed` with at least one `REVIEW`-outcome `RuleEvaluation`.
- An `ApprovalWorkflow` exists matching the trigger condition (e.g., risk tier, contract value
  tier).

### Main flow
1. System determines the required `approver_role`(s): if multiple `REVIEW` rules fired with
   different `approver_role`s, the required approver is the highest-severity rule's role; ties are
   broken by requiring all distinct roles named — escalate rather than under-notify
   (`docs/03-domain/policy-engine.md`, "Rule priority & conflicting rules").
2. System instantiates one or more `ApprovalRequest`s from the matching `ApprovalWorkflow`'s steps,
   each with `status = pending`, and emits `approval.requested` per request.
3. Named approver(s) are notified (in-app and, per `INT-002`, via webhook for
   `approval.required` for any connected integration).
4. Approver reviews the synthesized decision context (WHY/EVIDENCE/POLICY/RISK, per UC-6/UC-7's
   output) and resolves the request: `approved` or `rejected`, with an optional (recommended) or
   mandatory (on rejection) justification.
5. System validates that the resolving actor's `Membership` role matches the request's
   `approver_role` (`BR-APR-001`, `APR-002`) before accepting the resolution.
6. System records the resolution, sets `ApprovalRequest.status` accordingly, and emits
   `approval.approved` or `approval.rejected`.
7. If the workflow has multiple ordered steps (`APR-003`, e.g., Legal then Director), the next
   step's `ApprovalRequest` is instantiated only after the prior step resolves `approved` — a
   rejection at any step blocks progression to the next step (see Alternative flow A2).
8. Once all required steps resolve `approved`, control passes to UC-9 to finalize the `Decision`.

### Alternative flows
- **A1 — Single-step approval**: the common case for `medium`-severity `REVIEW` — one
  `ApprovalRequest`, one approver, one resolution, straight to UC-9.
- **A2 — Rejection blocks the chain** (`BR-APR-002`): if any required `ApprovalRequest` in the
  workflow is rejected, the overall `Decision` cannot reach `APPROVE` without an explicit override
  (UC-10) — rejection is a real stop, not a step that can be silently bypassed by a later approver
  in the chain.
- **A3 — SLA expiration** (`BR-APR-003`): an `ApprovalRequest` that exceeds its configured SLA
  (exact duration is a documented `TBD`) transitions to `expired` and emits an escalation event,
  surfacing the stalled request to the Admin/a designated escalation role rather than leaving it
  silently pending indefinitely.
- **A4 — Multi-step high-severity chain** (`APR-003`): e.g., `FIN-004`'s "very high-value contract"
  rule requires Legal **and** Director approval — both steps must resolve `approved` in sequence (or
  in parallel, per the specific `ApprovalWorkflow` configuration) before UC-9 finalizes.

### Failure cases
- **Wrong-role resolution attempt** (`BR-APR-001`): a user without the matching `approver_role`
  attempts to resolve a request; rejected with an authorization error; the `ApprovalRequest` remains
  `pending`; the attempt is still audited as a denied-access event.
- **No `ApprovalWorkflow` configured for the trigger condition**: the `REVIEW` outcome cannot be
  routed; this is surfaced as a configuration gap to `Admin` — the system does not silently default
  to auto-approve or auto-block in the absence of a workflow, since either default would be an
  unexplained, unaccountable decision.
- **Approver resolves without required justification on rejection**: rejected client-side/
  server-side; `justification` is mandatory on `rejected` resolutions by product design (mirroring
  the mandatory-justification pattern used for overrides, `BR-DEC-003`).

### Outputs
- One or more resolved `ApprovalRequest` records.
- A signal to UC-9 that the review is ready for final `Decision` packaging.

### Business rules
- `BR-APR-001`: role-matching required to resolve.
- `BR-APR-002`: rejection blocks `APPROVE` without override.
- `BR-APR-003`: SLA expiration and escalation.

### Permissions
- Resolve: the specific `Role` matching `approver_role` on the request (`Legal`, `Compliance`,
  `Privacy`, `Security`, `Finance`, or `Approver`).
- View own queue: the assigned approver role.
- View all requests (org-wide): `Admin`, `Auditor` (read-only).

### Audit events
- `approval.requested`, `approval.approved`, `approval.rejected`; SLA expiration escalation event
  (name per `docs/03-domain/audit.md`).

### Security considerations
- Role-matching enforcement (`BR-APR-001`) is a hard authorization check at the point of resolution,
  not just a UI-level queue filter — a user must never be able to resolve a request via direct API
  access simply because they can see it.
- `ApprovalRequest` resolution is immutable once resolved (`domain-model.md`) — no "undo" path
  exists; correcting a mistaken approval requires the explicit override mechanism (UC-10), which is
  itself audited, rather than allowing quiet mutation of the approval record.

### Data created
- `ApprovalRequest` (one or more).

### Dependencies
- Requires a completed `ComplianceReview` with a `REVIEW`-tier aggregated outcome (UC-5, informed by
  UC-7's severity ranking).
- Requires a configured `ApprovalWorkflow` (`ADR-006`).
- Feeds UC-9 (Decision Generation).

---

## UC-9: Decision Generation

### Purpose
Produce the final, packaged, explainable `APPROVE/REVIEW/BLOCK` `Decision` for a `ComplianceReview`
— the single artifact that answers "can we hire this supplier and sign this contract?" — using the
deterministic aggregation algorithm defined in `ADR-010`.

### Actors
- **Primary**: system.

### Inputs
- The completed `ComplianceReview`'s full `RuleEvaluation` set (UC-5).
- Resolved `ApprovalRequest`(s), if any were required (UC-8).

### Preconditions
- `ComplianceReview.status = completed`.
- If any `RuleEvaluation` outcome was `REVIEW`, all required `ApprovalRequest`s for that review have
  reached a terminal state (`approved`, `rejected`, or `expired`) — see Alternative flows for how
  each terminal state maps to the final `Decision`.

### Main flow
1. System aggregates all `RuleEvaluation` outcomes for the `ComplianceReview` per `ADR-010`/
   `BR-CMP-002`: **any `BLOCK` → final status `BLOCK`**; else **any `REVIEW` → final status
   `REVIEW`**; else **`APPROVE`** (fully automatic, no human step needed).
2. If the aggregated preliminary status is `REVIEW` and all required `ApprovalRequest`s resolved
   `approved` (UC-8), the final `Decision.status` becomes `APPROVE`.
3. If any required `ApprovalRequest` resolved `rejected`, the final `Decision.status` remains
   `REVIEW`'s negative resolution — effectively blocking progression to `APPROVE` (`BR-APR-002`)
   unless a subsequent manual override (UC-10) is invoked.
4. System creates the `Decision` record: `compliance_review_id`, `status`, `valid_until` (derived
   from policy configuration, default duration a documented `TBD` pending commercial input),
   `supersedes_decision_id` (set if this decision replaces an expired/superseded prior one),
   `overridden = false`.
5. System emits `decision.created`.
6. System hands the `Decision` to UC-11 (Evidence Packaging) automatically.

### Alternative flows
- **A1 — Fully automatic APPROVE**: every `RuleEvaluation` is `PASS`/`NOT_APPLICABLE`; no
  `ApprovalRequest` is ever created (UC-8 is skipped entirely); `Decision.status = APPROVE` is
  produced directly from step 1, with `valid_until` set and no human touchpoint required — this is
  the intended fast path for low-risk, policy-clean suppliers/contracts.
- **A2 — Immediate BLOCK**: any `BLOCK`-outcome `RuleEvaluation` (e.g., a sanctions hit or a missing
  DPA under `LGPD-001`) short-circuits straight to `Decision.status = BLOCK`; per the Policy Engine's
  DSL, `BLOCK` rules carry no `approver_role` (they are "not overridable without an explicit override
  action" per `docs/03-domain/policy-engine.md`'s rule DSL comment) — a `BLOCK` can only be reversed
  via UC-10's manual override, never auto-resolved by an approval step.
- **A3 — Re-evaluation supersedes a prior decision** (`BR-DEC-004`): triggered by `valid_until`
  expiry or a relevant `PolicyVersion`/`ContractVersion` change; produces a new `Decision` with
  `supersedes_decision_id` pointing at the prior one; the prior `Decision` is never edited
  (`BR-DEC-002`).

### Failure cases
- **Aggregation attempted before all required approvals resolved**: blocked by precondition —
  `Decision` generation does not proceed while any required `ApprovalRequest` remains `pending`; the
  `ComplianceReview` simply waits.
- **Conflicting rule outcomes misinterpreted as needing manual tie-breaking**: not a real failure
  mode by design — `ADR-010` explicitly makes aggregation order-independent and rejects "first-
  matching-rule-wins" specifically to eliminate this class of ambiguity; if an implementation ever
  requires manual tie-breaking between rule outcomes to determine the final status, that is a defect
  against `ADR-010`, not expected behavior.

### Outputs
- A `Decision` record (`APPROVE|REVIEW|BLOCK`) — the canonical answer to "can we hire this supplier
  and sign this contract?"

### Business rules
- `BR-CMP-002`: order-independent aggregation.
- `BR-DEC-001`: the exact `PolicyVersion` used is preserved on the `Decision`.
- `BR-DEC-002`: `Decision` immutability; re-evaluation creates a new `Decision` with
  `supersedes_decision_id`.
- `BR-DEC-004`: expiration/change triggers `compliance.review_required`.

### Permissions
- Trigger: automatic (system).
- View: broad, same as UC-6 view set; the `Decision` itself is typically the single most-viewed
  record by every role since it's the answer everyone is waiting for.

### Audit events
- `decision.created`.

### Security considerations
- `Decision` immutability (`BR-DEC-002`) is foundational to the entire evidence/audit story — any
  code path that allows in-place mutation of a `Decision` (bypassing the supersede-with-new-record
  pattern) is a critical defect, not a minor one, since it would let history be silently rewritten.
- The aggregation function itself must be pure and deterministic given its `RuleEvaluation` inputs —
  no hidden state, no reliance on wall-clock time or external calls at aggregation time — so that a
  `Decision` can be independently recomputed/verified later purely from its recorded evidence
  (directly supports UC-12's public verification goal).

### Data created
- `Decision`.

### Dependencies
- Requires a completed `ComplianceReview` (UC-5) and, when applicable, resolved `ApprovalRequest`s
  (UC-8).
- Triggers UC-11 (Evidence Packaging) automatically.

---

## UC-10: Manual Override of a Decision

### Purpose
Let an authorized human override a computed `Decision` when their judgment genuinely differs from
the automated outcome — while making absolutely certain the override is visible, justified, and
never erases the original evaluation.

### Actors
- **Primary**: Legal Counsel, Compliance Officer, or another role matching the relevant
  `approver_role`, per organization configuration — override authority is itself RBAC-gated
  (`ADR-003`).

### Inputs
- An existing `Decision` (any status: `APPROVE`, `REVIEW`, or `BLOCK`).
- A mandatory written justification.

### Preconditions
- Actor holds a `Role` authorized to override (typically `Legal`, `Compliance`, or `Admin`; exact
  per-organization configuration may vary, but the actor must always match an `approver_role`-
  equivalent authorization check — never a bare `Viewer` or unrelated functional role).
- The `Decision` exists and has not already been superseded by a later `Decision`.

### Main flow
1. Authorized actor opens a `Decision` they believe should be overridden (most commonly a `BLOCK`
   they judge to be a false positive, or a `REVIEW` they want to resolve differently than the
   approval chain resolved it).
2. Actor selects "Override Decision" and is required to enter a non-empty justification string —
   the UI does not allow submission without it (`BR-DEC-003`).
3. System validates the actor's role authorization for override.
4. System records the override as a `decision.overridden` audit event, capturing
   `original_outcome`, `justification`, and `overridden_by` (`ADR-010` §3).
5. System sets `Decision.overridden = true` and `override_justification` on the record.
6. Critically, the original `RuleEvaluation` records that produced the pre-override outcome are
   **never mutated or deleted** — the override is additive, recorded state, not a rewrite
   (`BR-DEC-003`, `BR-CMP-003`).
7. The overridden `Decision`'s effective status (as reflected everywhere downstream — dashboards,
   the Decision Passport, the contract's apparent go/no-go state) reflects the override, while the
   Decision Passport (UC-11) preserves and surfaces both the original computed outcome and the
   override, so nobody reading the passport later can mistake an override for an unremarkable
   automatic approval.

### Alternative flows
- **A1 — Override of a `BLOCK`**: since `BLOCK`-triggering rules carry no `approver_role` (they are
  not resolvable through the normal approval chain by design), this override mechanism is the
  *only* path to reverse a `BLOCK` — reinforcing why the justification and audit requirements here
  are non-negotiable; a `BLOCK` override is the single highest-scrutiny action in the product.
- **A2 — Override after a rejected `ApprovalRequest`** (`BR-APR-002`): when a required approval was
  rejected, blocking `APPROVE`, an authorized actor (typically a more senior role than the original
  rejecting approver, per organization configuration) can override to reach `APPROVE` — again
  requiring mandatory justification and full audit visibility of both the original rejection and the
  override.
- **A3 — Reversing an `APPROVE` to a stricter outcome**: less common but supported — e.g., new
  information surfaces post-approval (a supplier's sanctions status changes) and an authorized actor
  wants to record the contract as effectively blocked pending re-review; this follows the same
  override mechanism, and in practice usually triggers a fresh `compliance.review_required` cycle
  (UC-5 A2) rather than standing alone.

### Failure cases
- **Missing justification**: submission rejected client-side and server-side; no override recorded
  (`BR-DEC-003` treats a silent override as categorically disallowed, not merely discouraged).
- **Actor lacks override authorization**: rejected with an authorization error; the attempt is
  audited as a denied-access event.
- **Attempt to override a `Decision` that has already been superseded** by a newer `Decision`
  (`supersedes_decision_id` chain, `BR-DEC-002`): rejected — overrides apply to the current/live
  decision, not to stale history; the actor is directed to the current `Decision` instead.

### Outputs
- The `Decision` record updated with `overridden = true` and `override_justification` set (the
  record itself is still never "edited in place" in the sense of losing its original computed
  status — that remains visible alongside the override, per `ADR-010` §3's field design).
- A `decision.overridden` audit event.

### Business rules
- `BR-DEC-003`: override requires mandatory non-empty justification; itself audited; never silent.
- `BR-CMP-003`: original `RuleEvaluation` records untouched.
- `ADR-010` §3: override semantics in full.

### Permissions
- Override: role matching the required `approver_role` for the relevant rule category, or `Admin`/
  `Legal`/`Compliance` per organization's specific override-authority configuration — never a role
  with no approval authority in the relevant category.
- View override history: same broad view set as other decision-related use cases; overrides are
  never hidden from any role that could see the original `Decision`.

### Audit events
- `decision.overridden`.

### Security considerations
- This is one of the two or three highest-scrutiny actions in the entire product (alongside
  publishing a `PolicyVersion` and anchoring evidence) precisely because it lets a human reverse a
  deterministic, evidence-based outcome — the product's defense against misuse is total
  transparency (mandatory justification, immutable audit event, permanent visibility in the Decision
  Passport) rather than restricting who can do it so tightly that legitimate business judgment calls
  become impossible.
- Override authorization must be checked server-side on every attempt, never trusted from client
  state, given how consequential a successful override is.

### Data created
- Update to `Decision` (`overridden`, `override_justification` fields) — the `Decision` row itself
  is mutated for these two fields specifically, which is a deliberate, narrow, and fully-audited
  exception to the platform's general immutability posture for decision-related records; the
  `RuleEvaluation` set underneath remains fully immutable.

### Dependencies
- Requires an existing `Decision` (UC-9).
- Feeds into UC-11 (Evidence Packaging), which must reflect the override in the Decision Passport.

---

## UC-11: Evidence Packaging

### Purpose
Assemble the complete, hashable, self-contained bundle of evidence behind a `Decision` — the
Decision Passport's underlying payload — so that "why was this approved/blocked" is answerable in
full, from one artifact, indefinitely into the future.

### Actors
- **Primary**: system (`Evidence & Audit` bounded context).

### Inputs
- A `Decision` (from UC-9, potentially reflecting a UC-10 override).
- All referenced evidence: `Document` hashes, `Clause` citations, `SupplierCheck` results,
  `RuleEvaluation` records, `PolicyVersion` (with version number), `ApprovalRequest` resolutions and
  resolver identities, and — if applicable — the override record.

### Preconditions
- `Decision` exists (`decision.created` has fired, or `decision.overridden` for an overridden
  decision).

### Main flow
1. System collects every piece of evidence referenced by the `Decision`'s `ComplianceReview`: for
   each `RuleEvaluation`, its `evidence_refs` (specific `Clause`s and `SupplierCheck` results); the
   `PolicyVersion` (with version number) that was evaluated; every `Document`'s `content_hash`;
   every `ApprovalRequest`'s resolution and resolver identity; and the override record if one
   exists.
2. For each atomic piece, system creates an immutable `Evidence` record (`type`, `ref_id`,
   `content_hash`).
3. System computes a deterministic Merkle root over the full `Evidence` set (`EVD-002`, `BR-EVD-
   001`) — deterministically recomputable from the `Evidence` set at any future time, which is what
   makes independent verification (UC-12) possible without trusting JuriSense's database state.
4. System creates the `EvidencePackage` record (`decision_id`, `merkle_root`, `created_at`) and
   emits `evidence.package_created`.
5. This assembled package **is** the Decision Passport referenced throughout
   `docs/00-project/overview.md` — decision id, supplier, contract, document hashes, policies
   evaluated (with version), rules triggered, external sources consulted, AI executions (model/
   prompt version), reviewers, final decision, and timestamp, all traceable from this one bundle.
6. `EvidencePackage.status` moves from `created` toward `anchored`, handing off to UC-12
   automatically.

### Alternative flows
- **A1 — Re-evaluation produces a new package**: a new `Decision` (whether from expiry, policy
  change, or override — UC-9 A3, UC-10) always produces its own new `EvidencePackage`; packages are
  never edited or merged (`domain-model.md`: "immutable; a new `Decision` produces a new
  `EvidencePackage`").

### Failure cases
- **Referenced evidence is missing/inconsistent** (e.g., a `RuleEvaluation`'s `evidence_refs` points
  to a `Clause` that somehow cannot be resolved): package assembly fails loudly rather than silently
  omitting the missing reference — an incomplete Evidence Package is worse than a delayed one, given
  the product's core promise depends on completeness.
- **Merkle root computation is non-deterministic across runs** (a defect, not an expected failure
  mode): treated as a release-blocking correctness bug (`BR-EVD-001` is a hard invariant, not a
  best-effort target) — this would break UC-12's verification story entirely if it ever shipped.

### Outputs
- A complete, immutable `EvidencePackage` with its `Evidence` set and `merkle_root`.

### Business rules
- `EVD-001`: complete package assembly for every `Decision`.
- `EVD-002`/`BR-EVD-001`: deterministic Merkle root.
- `BR-EVD-002`: no raw contract text or personal data included in anything destined for on-chain
  anchoring (elaborated in UC-12; this use case must produce hashes/commitments suitable for that
  constraint, not raw content, at the `Evidence` layer itself).

### Permissions
- Trigger: automatic (system).
- View: `Legal`, `Compliance`, `Auditor` (full), `Procurement`/`Finance`/`Privacy`/`Security`
  (scoped to their relevant evidence), `Admin`.

### Audit events
- `evidence.package_created`.

### Security considerations
- `Evidence.content_hash` values must never themselves be reversible to raw confidential content by
  construction (they are hashes of content, not the content) — this is the property UC-12's public
  verification page depends on to be safely public.
- Access to the full `EvidencePackage` (as opposed to its public hash/proof) remains tenant-scoped
  and role-scoped like everything else (`SEC-001`) — only the anchored hash and verification proof
  are ever exposed publicly (UC-12); the underlying evidence detail is not.

### Data created
- `Evidence` (multiple), `EvidencePackage`.

### Dependencies
- Requires a `Decision` (UC-9/UC-10).
- Triggers UC-12 (Blockchain Anchoring) automatically.

---

## UC-12: Blockchain Anchoring and Public Verification

### Purpose
Anchor the `EvidencePackage`'s hash on a public, tamper-evident ledger and expose a public
verification page, so that "was this evidence altered after the fact?" has an answer that does not
require trusting JuriSense's own database — the product's core auditability-that-survives-time
promise made concrete.

### Actors
- **Primary**: system (via the `AnchoringProvider` interface, `ADR-007`).
- **Secondary**: any external party performing verification (auditor, regulator, acquirer's
  due-diligence team, the customer itself) — this actor does not need a JuriSense account.

### Inputs
- The `EvidencePackage.merkle_root` (from UC-11).
- The configured `AnchoringProvider` adapter (`ADR-007`; provider selection is a Phase 8 technical-
  spike decision — see the `TBD` note below).

### Preconditions
- `EvidencePackage` exists and is complete (UC-11).

### Main flow
1. System calls `AnchoringProvider.submit_hash(evidence_hash)` with the `EvidencePackage.merkle_root`
   — and **only** the hash; never raw contract/supplier data (`ADR-007`, `BR-EVD-002`, `EVD-004`).
2. System creates a `BlockchainAnchor` record with `status = submitted`, `evidence_package_id`,
   `provider`, `submitted_at`.
3. Once the underlying ledger confirms the transaction, system retrieves the proof via
   `AnchoringProvider.get_proof(anchor_ref)`, stores `anchor_ref` and `proof`, sets
   `BlockchainAnchor.status = confirmed`, and emits `evidence.anchored`.
4. `EvidencePackage.status` moves to `anchored`.
5. System publishes a public verification page (`docs/06-blockchain/verification.md`) accessible via
   a stable URL/decision id, exposing: the anchored hash, the anchor reference, the anchoring
   timestamp, and a "Verify" action.
6. An external party visits the verification page and triggers `AnchoringProvider.verify
   (evidence_hash, proof) -> bool`, which independently confirms — using the public ledger itself,
   not JuriSense's database — that the hash was anchored at the claimed time and has not been
   altered since.

### Alternative flows
- **A1 — Verification against a re-supplied evidence package** (deeper verification, for a party
  with access to the underlying evidence, e.g., the customer's own auditor with platform access):
  the verifier recomputes the Merkle root from the `Evidence` set themselves (`BR-EVD-001`:
  deterministically recomputable) and compares it against the publicly anchored hash — this is the
  strongest verification level, proving not just "a hash was anchored" but "this specific evidence
  produces that exact hash."
- **A2 — Anchoring provider migration**: because all anchoring goes through the `AnchoringProvider`
  interface (`ADR-007`), a future change of underlying chain/provider does not invalidate
  previously-anchored `BlockchainAnchor` records — each retains its own `provider` field and remains
  independently verifiable against whichever ledger it was actually submitted to.

### Failure cases
- **Anchoring submission fails/times out**: `BlockchainAnchor.status` remains `submitted` with a
  retry policy; `EvidencePackage.status` remains `created` (not yet `anchored`) — the `Decision`
  itself is already valid and usable internally (UC-9/UC-10 already completed) even before anchoring
  confirms; anchoring adds independent third-party verifiability on top of an already-valid decision,
  it does not gate the decision's own validity. This distinction matters operationally: a slow or
  temporarily unavailable anchoring provider must never block procurement from proceeding on an
  otherwise-valid `APPROVE`.
- **Anchoring provider permanently unavailable** (e.g., provider deprecated): `BlockchainAnchor`
  marked `failed`; system alerts for manual intervention/provider reconfiguration; the
  `EvidencePackage` and its Merkle root remain valid and independently recomputable regardless — the
  blockchain anchor is a verifiability enhancement, not the source of truth itself (the source of
  truth is the recorded evidence; the anchor proves it wasn't altered).
- **Public verification page queried for a non-existent/never-anchored decision**: returns a clear
  "not yet anchored" or "not found" state — never a false-positive verification result.

### Outputs
- A `BlockchainAnchor` record (`submitted → confirmed|failed`).
- A public verification page for the decision.

### Business rules
- `BR-EVD-002`/`EVD-004`: no raw contract text or personal data ever included in the on-chain
  payload — only hashes/commitments.

### Permissions
- Trigger anchoring: automatic (system).
- View `BlockchainAnchor` detail (internal, full): `Legal`, `Compliance`, `Auditor`, `Admin`.
- Access public verification page: unauthenticated, by design — this is the one surface in the
  entire product explicitly meant to be usable without a JuriSense account (`docs/06-blockchain/
  verification.md`).

### Audit events
- `evidence.anchored`.

### Security considerations
- The public verification page must expose only the hash, anchor reference, timestamp, and a verify
  action — never any underlying evidence content, contract text, or personal data (`BR-EVD-002` is
  the load-bearing constraint on this entire use case's public-facing surface; a defect here would
  be a severe LGPD/confidentiality incident, not a minor bug).
- Since the anchoring provider choice is still a Phase 8 technical-spike decision, the public
  verification page's implementation must be built against the provider-agnostic
  `AnchoringProvider` interface, not against any specific chain's SDK, so the choice below does not
  require reworking this use case's user-facing contract.

Status: TBD / Current preferred option: Constellation Network as primary candidate, a generic
EVM-compatible L2 testnet (Base Sepolia or Polygon Amoy) as the safest fallback, ICP/Caffeine AI
evaluated only if integration effort proves unusually low / Why undecided: the Phase 8 technical
spike benchmarking SDK maturity, integration effort, transaction cost, and hackathon bounty-track
fit has not yet run / Resolution: complete the Phase 8 spike and select the default adapter; `ADR-
007` moves from Proposed to Accepted at that point / Decision artifact: `ADR-007-blockchain-
anchoring-provider.md` and `docs/06-blockchain/anchoring-providers.md`.

### Data created
- `BlockchainAnchor`.

### Dependencies
- Requires a complete `EvidencePackage` (UC-11).
- Depends on the `AnchoringProvider` interface (`ADR-007`) and its eventual concrete adapter
  (pending Phase 8 spike, see `TBD` above).
- Is the terminal use case in the pipeline described in `docs/00-project/overview.md`.
