# Fallback MVP — The Hackathon Cut

> This is the explicit, minimal scope for the hackathon submission. Roadmap phase numbers below
> follow the pipeline order documented in `docs/00-project/overview.md` (Supplier → verification →
> ingestion → extraction → policy → compliance engine → approve/review/block → human approval →
> decision passport → audit trail → blockchain verification) and the phase boundary explicitly
> stated there — "an explicit Hackathon Cut after Phase 8 (Evidence/Audit + a working blockchain
> anchor)." The authoritative phase-by-phase roadmap (objectives, deliverables, dependencies, exit
> criteria, risks) lives in `docs/09-planning/roadmap.md`, owned separately; this document only maps
> each Hackathon Cut item to the phase it belongs to and defines the floor below which that item must
> not be cut further.

**Governing rule for every fallback below**: if a real integration proves too slow or unreliable to
finish, degrade to a manual/stubbed version **that is clearly labeled as such in the UI** (e.g., a
"demo mode" badge). Never silently fake a real-looking automated check — a judge, a future customer,
or a future auditor discovering that a "verified" badge meant nothing is far more damaging than an
honest "manual entry — demo mode" label.

## 1. Organization creation

- **Roadmap phase**: Phase 0–1 (Foundation / Identity & Organizations).
- **Full version**: multi-tenant `Organization` creation with plan selection, `Membership` invites,
  role assignment (`docs/03-domain/domain-model.md` — `Organization`, `Membership`, `Role`).
- **Minimum viable fallback**: a single pre-seeded `Organization` ("Acme Tecnologia Ltda.") with two
  or three pre-seeded `Membership` records (an admin and a `legal`-role approver) created via a
  setup script rather than a polished onboarding UI. The demo does not need to show organization
  *creation* live — it needs the organization to already exist correctly. If even self-serve signup
  is unfinished, that is acceptable as long as the seeded org and roles are real, working records
  exercised by the rest of the pipeline, not hardcoded demo-only shortcuts elsewhere in the code.

## 2. Supplier + CNPJ/sanctions check

- **Roadmap phase**: Phase 2 (Suppliers).
- **Full version**: `Supplier` creation triggers a live `SupplierCheck` against real CNPJ registry
  and CEIS/CNEP/CEPIM sanctions/restriction-list sources, populating `SupplierProfile`
  automatically.
- **Minimum viable fallback**: if the live source integration proves too slow or too unreliable to
  finish and harden in time, fall back to **manual data entry of the supplier's registry/sanctions
  status**, with a clearly visible "Demo mode — manual data entry, not a live registry check" badge
  on the `SupplierProfile` view and in the Decision Passport's "sources consulted" field. The
  `SupplierCheck` record structure (immutable, timestamped, `sources_consulted` field) stays real
  either way — only whether the check hits a live external API or a manual form differs, and that
  difference must be visible to the viewer, not hidden.

## 3. Contract upload

- **Roadmap phase**: Phase 3 (Contracts & Documents).
- **Full version**: PDF/DOCX/TXT upload with virus scanning, S3-compatible storage (`ADR-008`),
  SHA-256 `content_hash` computed on upload.
- **Minimum viable fallback**: PDF-only upload is sufficient for the demo (DOCX/TXT support can slip
  without weakening the demo narrative). The `content_hash` computation is **not** cuttable — it is
  the first link in the evidence chain that eventually gets anchored on-chain, and skipping it would
  make the blockchain-anchoring story hollow.

## 4. AI structured extraction

- **Roadmap phase**: Phase 3–4 (Contract Intelligence / AI Services).
- **Full version**: full schema extraction (parties, value, duration, renewal/termination, liability,
  confidentiality, IP, DPA terms, jurisdiction, guarantees, penalties, obligations, deadlines) with
  clause-level citations for every field, per `docs/05-ai/structured-extraction.md`.
- **Minimum viable fallback**: extraction can be scoped down to only the fields the demo scenario
  actually evaluates — contract value, duration, renewal type, liability type, personal-data
  processing flag, DPA presence — as long as **each of those fields still carries a real
  clause/page citation back to the source document**. Provenance is not cuttable: a field with no
  citation undermines the "never a black-box summary" claim that differentiates this product from a
  generic LLM contract-summarizer demo. If confidence scoring or the full extraction schema is
  incomplete, that is an acceptable, disclosed gap; a fabricated or uncited field is not.

## 5. Policy Engine evaluation

- **Roadmap phase**: Phase 4 (Policy Engine).
- **Full version**: full CEL-compiled Rule DSL (`ADR-004`), a rule authoring UI, simulation/dry-run
  mode, versioned `PolicyVersion` publishing workflow.
- **Minimum viable fallback**: the rule authoring UI can be cut entirely — the demo's `PolicyVersion`
  (containing `LGPD-001`, `LEGAL-008`, `FIN-003`, and ideally `FIN-004`/`SANC-001`) can be
  seeded directly as compiled rule data rather than built through a form. What is **not** cuttable is
  that the rules actually execute against the normalized evaluation context and produce real
  `RuleEvaluation` outcomes — a hardcoded "this contract is BLOCK" shortcut would falsify the entire
  demo and must never be used, even under time pressure.

## 6. Compliance Decision (APPROVE / REVIEW / BLOCK)

- **Roadmap phase**: Phase 5 (Compliance Engine).
- **Full version**: full `ComplianceReview` → `RuleEvaluation` set → `Decision` pipeline with the
  `ADR-010` aggregation, exception/override handling, and `valid_until` expiration.
- **Minimum viable fallback**: exceptions and manual overrides (`ADR-010` §3, policy-engine.md
  "Exceptions & manual overrides") can be cut from the hackathon build — they are real product
  features but not required to tell the demo story. The core aggregation algorithm itself (any
  BLOCK → BLOCK; else any REVIEW → REVIEW; else APPROVE) is the single most important piece of
  behavior in the whole product and must be implemented for real, not mocked.

## 7. Human approval step

- **Roadmap phase**: Phase 6 (Approvals & Decisions).
- **Full version**: configurable `ApprovalWorkflow` routing templates per risk tier
  (`ADR-006`), multi-step approval chains (Compliance + Legal + Director on HIGH risk).
- **Minimum viable fallback**: a single-step `ApprovalRequest` routed to whichever `Membership` holds
  the `legal` role (as the demo scenario requires) is sufficient — multi-step chains and
  organization-configurable workflow templates can be deferred. The approval action itself
  (approve/reject with mandatory justification, `ApprovalRequest.status` transition) must be a real
  state change, not a UI-only checkbox with no backing record.

## 8. Decision Passport

- **Roadmap phase**: Phase 7 (Approvals & Decisions / reporting layer).
- **Full version**: a polished, exportable (PDF/shareable-link) Decision Passport view assembling
  every field listed in `docs/00-project/overview.md` (decision id, supplier, contract, document
  hashes, policies evaluated with version, rules triggered, sources consulted, AI execution
  provenance, reviewers, final decision, timestamp).
- **Minimum viable fallback**: the export/PDF polish can be cut — a well-formatted in-app read-only
  view is enough for the demo. The **content completeness** of the passport is not cuttable: every
  field in that list must be genuinely populated from real records for the specific decision being
  demoed, because this view is what the "why was this approved?" claim rests on, live, in front of
  judges.

## 9. Blockchain evidence anchoring

- **Roadmap phase**: Phase 8 (Evidence & Audit) — the Hackathon Cut boundary.
- **Full version**: `EvidencePackage` with a deterministically recomputable Merkle root, submitted via
  the chosen default `AnchoringProvider` adapter (Constellation Network, pending the Phase 8
  technical spike per `ADR-007`), producing a confirmed `BlockchainAnchor`.
- **Minimum viable fallback**: if the Constellation SDK integration proves too slow to finish and
  harden by the Week 5 checkpoint (`docs/08-hackathon/submission-plan.md`), fall back immediately to
  the pre-identified alternative in `ADR-007` — a generic EVM-compatible L2 testnet (Base Sepolia or
  Polygon Amoy) with a minimal hash-anchoring contract — rather than cutting the blockchain step
  entirely. The `AnchoringProvider` interface (`submit_hash`/`get_proof`/`verify`) makes this swap
  cheap by design; **the interface and the "only hashes, never raw data, ever get anchored" rule are
  not cuttable under any time pressure**, since faking an anchor (e.g., a UI that shows a fabricated
  transaction ID with no real on-chain submission) would be exactly the kind of silently-faked
  automated check the governing rule above forbids, and would be actively dishonest to a Constellation
  bounty judge specifically.

## 10. Public verification page

- **Roadmap phase**: Phase 8 (Evidence & Audit) — same phase as item 9, the public-facing half of it.
- **Full version**: a polished, no-login public page per anchored decision, showing the anchor
  reference, provider, timestamp, and a live "Verify" action, plus general educational content about
  what the anchor does and does not prove.
- **Minimum viable fallback**: visual polish and educational copy can be minimal — a bare page is
  fine. What cannot be cut is that the "Verify" action performs a **real** call to
  `AnchoringProvider.verify(evidence_hash, proof) -> bool` against the live chain/testnet, not a
  hardcoded "✓ Verified" label. This is the single moment in the demo (`demo-scenario.md`, step 23)
  where the product's core trust claim is checked live in front of an audience — it is the last place
  in the entire Hackathon Cut where a shortcut would be acceptable, not the first.

## What is explicitly out of scope for the Hackathon Cut

Continuous supplier re-monitoring, deeper contract-clause negotiation tooling, standalone policy
management as a sellable product, broader third-party risk scoring, an open developer API, and
international jurisdiction packs beyond Brazil — these are real, documented, later roadmap phases
(`docs/01-product/future-product-vision.md`), not implied to exist in the submission, and should be
described in the pitch/write-up as "next," never demoed as if already built.
