# Demo Scenario

> Elaborated from the mission brief's demo scenario, using real entity and rule names from
> `docs/03-domain/domain-model.md`, `docs/03-domain/policy-engine.md`, and
> `docs/adr/ADR-010-decision-aggregation-model.md`, so the walkthrough is technically accurate to
> the domain, not just narratively plausible. Written as a numbered script a presenter can follow
> live. Where the presenter should narrate rather than click, that is called out explicitly.

## Setup (before the demo starts)

- An `Organization` ("Acme Tecnologia Ltda.", a fictional 200-person Brazilian SaaS company) already
  exists, with a published `PolicyVersion` containing at least the rules `LGPD-001`, `LEGAL-008`, and
  `FIN-003` (see `docs/03-domain/policy-engine.md` for the exact YAML). This setup step happens
  before the live demo, not during it — the presenter should say so explicitly ("this organization
  and its compliance policy were configured ahead of time; what you're about to see is the live
  supplier and contract workflow").
- The presenter narrates the premise in one sentence: *"Acme needs to hire a new SaaS vendor. Before
  anyone signs anything, JuriSense Gate has to answer: can we hire this supplier and sign this
  contract?"*

## Part 1 — Supplier verification

1. The presenter creates a new `Supplier` record for the vendor ("CloudDocs Software Ltda.") by
   entering its CNPJ. Narrate: *"Supplier starts in `prospect` status."*
2. Submitting the CNPJ triggers a `SupplierCheck` — a point-in-time verification run against
   official/external sources (company registry status, CEIS/CNEP/CEPIM sanctions/restriction lists).
   Narrate: *"This is `SupplierCheck.started`; it's immutable once completed — we never overwrite a
   verification run, we create a new one."*
3. The check completes (`supplier.check.completed`), producing/refreshing the `SupplierProfile`
   (registry status, corporate structure) and the `Supplier` transitions to `under_review`. Narrate
   the result: registry status active, no sanctions hits.

## Part 2 — Contract ingestion and AI extraction

4. The presenter uploads the vendor's proposed SaaS contract (PDF) as a `Document`. Narrate: *"The
   system computes a SHA-256 `content_hash` on upload — this hash is what eventually gets chained
   into the Evidence Package."*
5. A `Contract` is created linking to `Supplier` "CloudDocs Software Ltda.", and a first
   `ContractVersion` is created from the uploaded `Document`.
6. AI structured extraction runs against the `ContractVersion`, producing `extracted_data` and a set
   of `Clause` records with page/span citations. Narrate the extracted terms live, matching the
   locked demo numbers:
   - Contract value: **R$ 480,000/year**
   - Term: **24 months**
   - **Automatic renewal** clause present
   - Liability: **unlimited**
   - **Processes personal data**: yes
   - **DPA (Data Processing Agreement)**: absent
   Narrate: *"Every one of these fields traces back to a specific clause and page in the source
   document — this is provenance, not a black-box summary."*
7. `contract.analysis_completed` fires; the `ContractVersion` moves from `extracted` to `analyzed`.

## Part 3 — Policy Engine evaluation and the first decision

8. The presenter triggers a `ComplianceReview` for this `ContractVersion` against the organization's
   current `PolicyVersion`. Narrate: *"Policy & Compliance builds a normalized evaluation context
   first — flat fields like `contract.liability.type`, `contract.value.brl`,
   `contract.processes_personal_data`, `contract.dpa_present` — the rules never touch raw AI output
   directly."*
9. Three rules fire, each producing an immutable `RuleEvaluation`:
   - **`LGPD-001`** ("DPA Required for Personal Data Processing"): `processes_personal_data: true`
     and `dpa_present: false` → outcome **BLOCK**, severity `critical`, no approver role (a BLOCK
     from this rule is not overridable without an explicit override action).
   - **`LEGAL-008`** ("Unlimited Liability Requires Legal Review"): `contract.liability.type:
     unlimited` → outcome **REVIEW**, severity `high`, `approver_role: legal`.
   - **`FIN-003`** ("High-Value Contract Requires Legal Approval"): `contract.value.brl` = 480,000 ≥
     250,000 → outcome **REVIEW**, severity `medium`, `approver_role: legal`.
10. The `ComplianceReview` aggregates these three `RuleEvaluation`s per `ADR-010`'s algorithm: *any
    BLOCK → BLOCK*. Narrate explicitly, because this is the product's core explainability claim:
    *"Even though two rules only said REVIEW, one rule said BLOCK — and BLOCK always wins, because
    it's the safer failure mode. The aggregation is a pure function of the set of outcomes, not the
    order they ran in."*
11. A `Decision` is created with `status: BLOCK`, referencing all three `RuleEvaluation`s as its
    rationale. Narrate the output format the product always shows — never a bare status:
    *"WHY: missing DPA on a contract that processes personal data. EVIDENCE: clause citation +
    extracted field. POLICY: `LGPD-001`, v[N]. REQUIRED ACTION: add a DPA before this can proceed."*

## Part 4 — Correction and re-evaluation

12. The presenter narrates the vendor's response: *"CloudDocs corrects the contract — they add a DPA
    and cap liability at, say, 12 months of contract value instead of leaving it unlimited."*
13. A **new** `ContractVersion` is submitted for the same `Contract` (never an edit to the existing
    version — `ContractVersion` is immutable once created, per `docs/03-domain/domain-model.md`).
    AI extraction runs again on this version, now showing `dpa_present: true` and
    `liability.type: capped`.
14. A new `ComplianceReview` runs against the same current `PolicyVersion`:
    - `LGPD-001`: `dpa_present: true` → outcome **PASS**.
    - `LEGAL-008`: liability is no longer `unlimited` → outcome **PASS** (or, if the presenter
      chooses to keep liability capped-but-still-high for a richer demo beat, outcome **REVIEW**
      persists — narrate honestly whichever the actual extracted data yields; do not force an
      APPROVE if the rule condition still matches).
    - `FIN-003`: contract value is still R$ 480,000 ≥ 250,000 → outcome **REVIEW** persists
      regardless of the liability fix, since `FIN-003` is a value-threshold rule independent of
      liability terms.
15. Aggregation now yields **REVIEW** (no BLOCK fired; at least one REVIEW — `FIN-003`, and possibly
    `LEGAL-008` — still fired). Narrate: *"This is realistic, not a scripted 'everything turns green'
    moment — a R$ 480k/24-month contract still needs a human legal sign-off on value alone, even
    after the compliance blocker is fixed. The system doesn't over-claim automation where a human
    judgment call is genuinely warranted."*
16. A new `Decision` is created with `supersedes_decision_id` pointing at the original BLOCK
    `Decision` — the old decision is never edited or deleted, per `ADR-010`'s re-evaluation model.

## Part 5 — Human approval

17. Because the new `Decision` is REVIEW, an `ApprovalRequest` is instantiated with
    `approver_role: legal` (the highest-severity REVIEW rule's role, per the policy engine's
    escalation rule). Narrate: *"This routes to whoever holds the `legal` role in this
    organization's membership — not a hardcoded person."*
18. The presenter (playing the Legal approver) reviews the `ApprovalRequest`, sees the full rationale
    (which rules fired, which passed, the extracted clause citations), and approves it with a
    justification note. `ApprovalRequest.status` moves to `approved`.

## Part 6 — Decision Passport, evidence, and blockchain anchoring

19. With the `Decision` now resolved, the system packages a **Decision Passport**: decision id,
    supplier, contract, document hashes, the exact `PolicyVersion` evaluated, every `RuleEvaluation`
    (both the historical BLOCK ones and the current PASS/REVIEW ones), external sources consulted
    (the `SupplierCheck` run), the AI execution provenance (model/prompt version), the approver, and
    the timestamp. Narrate: *"Ask 'why was this approved?' two years from now, and this is the
    complete, reproducible answer — not 'someone probably looked at it.'"*
20. An `EvidencePackage` is built from the Decision Passport's constituent `Evidence` records (one
    per document hash, `SupplierCheck` result, and `RuleEvaluation`), and a `merkle_root` is computed
    deterministically over that evidence set.
21. The `merkle_root` is submitted through the `AnchoringProvider` interface (`ADR-007`) —
    `submit_hash(evidence_hash) -> anchor_ref` — to the selected default provider (Constellation
    Network, pending the Phase 8 spike; see `docs/08-hackathon/hackathon-strategy.md` §3.1). A
    `BlockchainAnchor` record is created, moving from `submitted` to `confirmed`. Narrate explicitly,
    because this is the point most likely to be misunderstood: *"Nothing about this contract or this
    supplier's personal data goes on-chain — only a hash of the evidence bundle. The chain proves the
    evidence wasn't altered after the fact; it is not a copy of the evidence."*

## Part 7 — Public verification

22. The presenter opens the **public verification page** for this `BlockchainAnchor` (no login
    required — this is the point of a public, third-party-checkable proof). The page shows: the
    `anchor_ref`, the provider, the submission timestamp, and a "Verify" action that calls
    `AnchoringProvider.verify(evidence_hash, proof) -> bool` live against the chain.
23. The presenter clicks "Verify" live, on stage, and the page confirms the hash matches what was
    anchored. Close the demo on this beat: *"Anyone — an auditor, a regulator, an acquirer's due
    diligence team, the vendor itself — can independently confirm this decision's evidence hasn't
    been tampered with, without trusting Acme's internal database or JuriSense's word for it. That's
    the product's core promise, proven live."*

## Notes for the presenter

- If blockchain confirmation latency is unpredictable on the chosen provider/testnet, pre-submit the
  anchor a few minutes before the live demo and show the confirmed state plus a *fresh* verify call
  live, rather than waiting on-stage for confirmation. Say so if asked — do not imply the anchor was
  submitted live if it was pre-staged; only the verification step needs to be live.
- If a judge asks "what if the AI extraction is wrong?", the honest answer is in
  `docs/00-project/overview.md`: AI is used for interpretation/extraction, never to unilaterally
  decide a compliance outcome — the deterministic Policy Engine rules are what actually gate
  APPROVE/REVIEW/BLOCK, and every extracted field carries a citation back to the source document for
  a human to check.
