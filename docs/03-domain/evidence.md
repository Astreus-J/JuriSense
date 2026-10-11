# Evidence & the Decision Passport

This document specifies the **Decision Passport** — the product-facing name for a `Decision`'s
`EvidencePackage` — in full: exactly what it contains, how `Evidence` entities compose into it, how
its Merkle root is computed conceptually, what long-term verifiability means operationally, and the
explicit privacy boundary that keeps confidential data off-chain. See `docs/03-domain/
domain-model.md` for entity definitions (`Evidence`, `EvidencePackage`, `AuditEvent`,
`BlockchainAnchor`), `docs/03-domain/business-rules.md` (`BR-EVD-*`) for invariants, `ADR-007` for
the anchoring-provider abstraction, and `docs/03-domain/audit.md` for the event catalog this
document's reconstruction model depends on.

## What the Decision Passport is

Per `docs/00-project/overview.md`: *"Every decision is packaged with: decision id, supplier,
contract, document hashes, policies evaluated (with version), rules triggered, external sources
consulted, AI executions (model/prompt version), reviewers, final decision, and timestamp — so 'why
was this approved?' is answerable months or years later."* The Decision Passport is this package,
made presentable and independently verifiable. It is the product's central trust artifact — the
answer JuriSense Gate gives, with proof, to *"Can we hire this supplier and sign this contract?"*

## Exactly what it contains

The `EvidencePackage` for a `Decision` is composed of the following, each backed by an immutable
domain entity or event referenced in `docs/03-domain/audit.md`:

| Field | Source |
|---|---|
| Decision id | `Decision.id` |
| Supplier | `Supplier.id`, `legal_name`, `tax_id`, plus the `SupplierProfile`/`SupplierCheck` current as of the review (`docs/03-domain/supplier-compliance.md`) |
| Contract | `Contract.id`, `ContractVersion.id`/`version_number` evaluated |
| Document hashes | `Document.content_hash` (SHA-256) for every `Document` backing the evaluated `ContractVersion`, plus any supporting-evidence documents referenced |
| Policies evaluated + version | `PolicyVersion.id`/`version_number` recorded on the `ComplianceReview` (`BR-DEC-001`) |
| Rules triggered | every `RuleEvaluation` (`rule_id`, `outcome`, `severity`, `rationale`, `evidence_refs`) belonging to that `ComplianceReview` |
| External sources consulted | `SupplierCheck.sources_consulted` (CNPJ registry, CEIS/CNEP/CEPIM — `docs/03-domain/supplier-compliance.md`) |
| AI executions (model/prompt version) | extraction run metadata attached to the `ContractVersion`'s `extracted_data` and each `Clause`, per `docs/05-ai/ai-strategy.md`'s AI Gateway logging (`ADR-005`) |
| Human reviewers | every `ApprovalRequest` resolution (`approved_by`/`rejected_by`) for the associated `ComplianceReview`, plus any `Decision.overridden_by` (`docs/03-domain/approvals.md`) |
| Final decision | `Decision.status` (`APPROVE|REVIEW|BLOCK`), and `overridden`/`override_justification` if applicable |
| Timestamp | `Decision.created_at` (and, for an override, `decision.overridden`'s `overridden_at`) |

**Product decision (reconfirmed 2026-10-10)**: the Supplier row above — `Supplier.id`,
`legal_name`, `tax_id` — is captured as a **point-in-time snapshot as of the decision**, not a live
reference re-read from the current `Supplier` row, for the same consistency reason the rest of this
table already reads from fixed, review-time state (`SupplierProfile`/`SupplierCheck` "current as of
the review", not "current as of whenever someone opens the Passport"). This is currently moot —
there is no feature yet that lets a `Supplier`'s `legal_name`/`tax_id` be edited after a `Decision`
references it, so today the snapshot and the live row are always identical. The decision is recorded
now so that whenever a supplier-edit feature ships, it's built against an already-settled answer
instead of silently defaulting to a live join that would make older Decision Passports describe a
supplier identity that didn't exist at decision time.

Each of these is represented internally as one or more `Evidence` records — `domain-model.md`:
*"one atomic piece of evidence referenced by a `Decision` (a document hash, a `SupplierCheck`
result, a `RuleEvaluation`)"* — each with a `type`, `ref_id` (pointing back to the source entity),
and its own `content_hash`.

## How Evidence entities compose into an EvidencePackage

```
Decision (status, valid_until, ...)
    │
    ▼
EvidencePackage (id, decision_id, merkle_root, created_at)
    │
    ├── Evidence[type=document_hash]        → Document.content_hash, one per contract Document
    ├── Evidence[type=rule_evaluation]       → RuleEvaluation.id, one per triggered/evaluated rule
    ├── Evidence[type=supplier_check]        → SupplierCheck.id (the one current at review time)
    ├── Evidence[type=policy_version]        → PolicyVersion.id + version_number
    ├── Evidence[type=ai_execution]          → AI Gateway execution record (model, prompt version)
    ├── Evidence[type=approval_resolution]   → one per resolved ApprovalRequest
    └── Evidence[type=override]              → present only if Decision.overridden is true
```

Assembly is triggered by `decision.created` (`docs/03-domain/audit.md`) and is a pure, deterministic
function of already-immutable data — `Evidence & Audit` does not compute or infer anything new at
this step; it only collects references and hashes of facts that already exist. This is what makes
`EVD-001` ("assemble a complete `EvidencePackage` for every `Decision`") a mechanical step rather
than a judgment call: everything it needs was already recorded, immutably, by the time
`decision.created` fires.

## Override addenda (product decision 2026-10-10, closing #187)

`override_decision` is the one documented exception to "never edited in place" (it changes
`Decision.status` in place, `BR-DEC-003`) -- but until this decision, it never touched the
`EvidencePackage` already assembled for that Decision, leaving anchored evidence silently stale
relative to the real, overridden outcome. Every override now also appends an
`EvidenceOverrideAddendum` to the package, in the same transaction as the Decision update and its
`decision.overridden` audit event:

```
EvidencePackage (merkle_root, sealed at creation/anchoring time)
    │
    └── EvidenceOverrideAddendum[sequence_number=1] (previous_hash=null)
            └── EvidenceOverrideAddendum[sequence_number=2] (previous_hash=addendum[1].content_hash)
                    └── ...
```

A Decision can be overridden more than once while it stays `ACTIVE`, so a package can accumulate
more than one addendum, not at most one. Each addendum's `content_hash` commits to its own fields
*and* the previous addendum's hash (`None` for the first), so the sequence itself is tamper-evident
and strictly ordered -- a chain, not an independent bag of rows (`app/evidence/domain/
override_addendum.py`). Deliberately kept OUT of the package's own Merkle tree: that tree is
sealed at package-creation time (and may already be anchored), while an addendum, by definition,
happens later. Addenda are append-only (the same DB trigger as `evidence`/`evidence_packages`,
`infrastructure/append_only.py`) and readable through the existing evidence-package API, but
wiring them into `BlockchainAnchor`/`AnchoringProvider` on their own is deliberately deferred --
today they strengthen the audit trail and are ready to anchor, but nothing submits them yet.

Once assembled, the `EvidencePackage` itself is immutable (`domain-model.md`): a re-evaluation never
edits an existing package — a new `Decision` (via `supersedes_decision_id`, `BR-DEC-002`) produces
its own new `EvidencePackage` from scratch, referencing its own `ComplianceReview`. Old packages are
never touched, so a Decision Passport retrieved for a past `Decision` always shows exactly what was
true and evaluated at that time, even if the supplier/contract/policy have all since changed.

## How the Merkle root is computed (conceptually)

`BR-EVD-001`: *"An `EvidencePackage`'s `merkle_root` must be deterministically recomputable from its
`Evidence` set at any time."* Conceptually:

1. Every `Evidence` record in the package contributes its own `content_hash` — for a document, this
   is the `Document.content_hash` computed at upload time (never recomputed, per
   `docs/03-domain/domain-model.md`); for non-document evidence (a `RuleEvaluation`, a
   `SupplierCheck` result, an AI execution record), `content_hash` is a hash of that record's
   canonical, deterministically-serialized representation (stable field order, stable encoding).
2. These leaf hashes are combined pairwise up a binary Merkle tree, in a fixed, deterministic
   ordering (e.g. sorted by `Evidence.id` or by a fixed `type` + `ref_id` ordering established once
   and never changed for the life of the schema) until a single root hash remains: the
   `merkle_root`.
3. Because every leaf input is itself immutable (documents are never recomputed; `RuleEvaluation`,
   `SupplierCheck`, `Decision`, and every other contributing entity are immutable once created/
   completed, per their respective `domain-model.md` lifecycles) and the tree-construction ordering
   is fixed, **the same `Evidence` set always produces the same `merkle_root`**, computed fresh, by
   anyone, at any point in the future — without needing to trust JuriSense Gate's own stored
   `merkle_root` value, only to recompute and compare it.
4. This is precisely the property that makes on-chain anchoring meaningful (`ADR-007`): only this
   single root hash is submitted via the `AnchoringProvider` interface
   (`submit_hash(evidence_hash) -> anchor_ref`) — a third party can later recompute the root from
   the retained `Evidence` set and compare it against the on-chain-anchored value
   (`docs/06-blockchain/verification.md`) to prove the evidence was not altered after the fact.

The exact hash algorithm, leaf-canonicalization format, and tree-construction library are an
implementation detail of `Evidence & Audit`'s Phase-8 build, not fixed by this document beyond the
determinism/recomputability requirement `BR-EVD-001` already mandates — see `ADR-007`'s own
still-open technical spike for the concrete `AnchoringProvider` choice, which is independent of
the hashing scheme itself.

## What "verifiable months or years later" means operationally

The Decision Passport's core promise only holds if reconstruction never depends on anything that
can disappear, change, or go offline. Concretely, this means:

- **No dependency on live external systems.** The CNPJ registry, CEIS/CNEP/CEPIM, or any future
  data source might change their published records, retire an API, or become unavailable — none of
  that matters, because the `SupplierCheck.raw_results` captured at check time is itself the
  retained evidence, not a pointer to re-query later. Re-verifying a Decision Passport never means
  "call Receita Federal again and see if it still agrees."
- **No dependency on the current state of mutable-looking entities.** `Supplier.status`,
  `Contract.status`, and the current `SupplierProfile`/`Policy` may all have moved on since the
  decision was made — the Passport reconstructs from the specific `SupplierCheck`, `ContractVersion`,
  and `PolicyVersion` ids the original `ComplianceReview` recorded, per `BR-DEC-001`, never from
  "whatever is current now."
- **No dependency on re-running AI.** The `extracted_data` and per-clause confidence scores are
  captured once, at extraction time, along with the model/prompt version used — the Passport does
  not require re-running extraction to reproduce or verify what was decided; it needs only to show
  what was extracted and at what confidence, at the time.
- **Reconstructable from `AuditEvent` + immutable entities alone.** As detailed in
  `docs/03-domain/audit.md`'s "How audit events support Decision Passport reconstruction" section,
  the entire chain from `decision.created` back through every contributing review, check, and
  document event can be walked purely from data already at rest in JuriSense Gate's own database —
  the on-chain anchor is the *independent, third-party-checkable* layer on top of that, not a
  replacement for it. Losing the anchoring provider (e.g. a chain going defunct) would degrade the
  independent-verification story but would not by itself make the underlying evidence
  unreconstructable, because the full evidentiary record lives in the immutable domain data first
  and the chain second.
- **Append-only guarantee underwrites all of the above.** None of this reconstruction is meaningful
  if past records could have been quietly edited — `BR-EVD-003`'s append-only `AuditEvent` guarantee
  (`docs/03-domain/audit.md`) is the foundation everything above stands on.

## Privacy boundary: what never goes on-chain

`BR-EVD-002`: *"No raw contract text, personal data, or confidential document content is ever
included in a `BlockchainAnchor` payload — only hashes/commitments."* This is absolute and applies
regardless of which `AnchoringProvider` is ultimately chosen (`ADR-007`):

- The `BlockchainAnchor` payload is the `merkle_root` (and whatever minimal provider-specific
  transaction metadata is required to submit it) — nothing else. No contract clause text, no
  supplier registry details, no reviewer names, no personal data of any kind is submitted on-chain.
- The full `Evidence`/`EvidencePackage` content — the actual clause text spans, supplier profile
  fields, reviewer identities — remains inside JuriSense Gate's own tenant-isolated database
  (`SEC-001`), never replicated to the chain. The chain only ever proves *"this exact hash existed
  and was anchored at this time"* — it is not a copy of the underlying evidence and was never
  intended to be one (`docs/00-project/overview.md`, "Why blockchain is NOT the product").
- This is a hashing/commitment boundary, not merely an access-control boundary: even an attacker
  with full read access to a public blockchain explorer learns nothing about the supplier, the
  contract, or the parties involved — only that *some* evidence bundle, identified by its hash,
  existed at a given time.
- The full privacy design — LGPD classification of what counts as personal data in this domain,
  retention rules, and the detailed technical mechanism keeping confidential content out of any
  on-chain-bound payload — is specified in `docs/06-blockchain/privacy.md`; this document only
  states the boundary as it pertains to Decision Passport composition and defers the full privacy
  treatment to that document.

## Relationship to other domain documents

- `EVD-001` through `EVD-004` (`docs/01-product/functional-requirements.md`) are the capability
  requirements this document specifies the behavior of.
- `BR-EVD-001` through `BR-EVD-003` are the authoritative invariants this document elaborates.
- `ADR-007` governs the `AnchoringProvider` abstraction and the still-open provider spike; `ADR-010`
  governs the `Decision` aggregation and override semantics that produce the "final decision" field
  in the Passport.
- `docs/03-domain/audit.md` is the event catalog and reconstruction-chain specification this
  document's "verifiable months or years later" section depends on.
- `docs/03-domain/supplier-compliance.md`, `docs/03-domain/contract-compliance.md`, and
  `docs/03-domain/approvals.md` specify how the supplier, contract, and approval evidence entering
  this package were produced in the first place.
- `docs/06-blockchain/privacy.md` (owned separately) is the authoritative, full privacy treatment
  cross-referenced above.
