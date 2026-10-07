# Evidence Model — From Decision to On-Chain Anchor

> Related: `docs/03-domain/domain-model.md` (`Evidence`, `EvidencePackage`, `BlockchainAnchor`,
> `Decision` entities), `docs/03-domain/business-rules.md` (`BR-EVD-001`, `BR-EVD-002`),
> `docs/00-project/overview.md` (product pipeline diagram), `ADR-007`,
> `docs/06-blockchain/anchoring-providers.md`, `docs/06-blockchain/privacy.md`.

This document elaborates the last stage of `docs/00-project/overview.md`'s product pipeline —
`Decision Passport → Audit Trail → Blockchain verification (evidence anchoring)` — into the concrete
technical flow: which hashes are computed, how they are assembled into a Merkle tree, and how that
tree's root is submitted through the `AnchoringProvider` interface.

## 1. The five hash inputs

Every `Decision` (`docs/03-domain/domain-model.md`) is backed by exactly one `EvidencePackage`,
which in turn holds one or more `Evidence` records. In practice, an `EvidencePackage` is built from
five categories of hashed input, each corresponding to one stage of the compliance pipeline:

| # | Hash | Source | What it commits to |
|---|------|--------|---------------------|
| 1 | **Contract Hash** | `Document.content_hash` (SHA-256, computed on upload — `docs/03-domain/domain-model.md`) of the `ContractVersion`'s source `Document`, plus the `ContractVersion.extracted_data` structured output | The exact contract text and the AI-extracted structured terms that were evaluated |
| 2 | **Policy Hash** | The `PolicyVersion` (`policy_id`, `version_number`, its full `Rule` set) that the `ComplianceReview` evaluated against | The exact rule set in force at decision time — this is what makes a historical decision reproducible per `ADR-010` |
| 3 | **Evidence Hash** | `SupplierCheck` results, `Clause` citations, and `RuleEvaluation` outcomes for that `ComplianceReview` | The factual findings the decision was based on (sanctions checks, clause-level provenance, per-rule pass/review/block outcomes) |
| 4 | **Decision Hash** | The `Decision` record itself: `status`, `valid_until`, `overridden`, `override_justification` (if any), timestamp | The final outcome and its rationale |
| 5 | **Approval Hash** | Resolved `ApprovalRequest` records, where the risk tier required human approval (`docs/03-domain/approvals.md`) | Who approved, in what role, when, and any justification |

Each of these is represented internally as one or more `Evidence` entities
(`type`, `ref_id`, `content_hash` — `docs/03-domain/domain-model.md`), all belonging to the same
`EvidencePackage`. A `ComplianceReview` that auto-approves at LOW risk (no `ApprovalRequest` needed)
simply omits category 5; every other category is always present.

## 2. Assembling the Evidence Package

The `EvidencePackage` (`decision_id`, `merkle_root`, `created_at`) is created once, when a `Decision`
is finalized, and is immutable from that point on (`docs/03-domain/domain-model.md`). Assembly is
deterministic:

1. Collect every `Evidence` item belonging to the `Decision`'s `ComplianceReview` (contract, policy,
   findings, decision, approval — as above).
2. Canonicalize each `Evidence` item's payload as JSON with a fixed, sorted key order (see
   `docs/06-blockchain/privacy.md` for the exact canonicalization and salting rules — this matters
   for `BR-EVD-001` recomputability and for preventing hash-guessing attacks).
3. Compute `content_hash = SHA-256(canonical_json)` for each item — this is the **leaf** value used
   in the Merkle tree below.
4. Sort the resulting leaves in a fixed, well-defined order (by `Evidence.type` then `Evidence.id`)
   so that the same evidence set always produces the same tree regardless of insertion order.
5. Build the Merkle tree bottom-up (§3) and store the resulting root as `EvidencePackage.merkle_root`.

Only the `merkle_root` — a single 32-byte hash — ever leaves JuriSense's systems. The full canonical
payloads and leaf hashes stay in tenant-isolated storage so that `BR-EVD-001` ("deterministically
recomputable from its `Evidence` set at any time") can be satisfied on demand, without ever having
put the underlying content anywhere public (`BR-EVD-002`, `docs/06-blockchain/privacy.md`).

## 3. Worked example (illustrative — all hash values below are fabricated for demonstration only)

Consider `Decision D-2026-00842`: a `ComplianceReview` of a contract renewal with supplier "Acme
Cloud Serviços Ltda.", resulting in `REVIEW` (escalated because of an unlimited-liability clause),
resolved to `APPROVE` after Legal sign-off.

**Step 1 — five canonicalized evidence items and their leaf hashes:**

```
L1 = SHA-256(canonical_json(ContractEvidence))
   = 3f2a9c1e7b4d8f60a1c5e9b2d4f7a8c3e6b1d9f4a7c2e8b5d1f6a3c9e7b4d8f2   (illustrative)

L2 = SHA-256(canonical_json(PolicyEvidence))
   = 8b1d4f7a2c9e6b3d8f1a5c7e9b2d4f6a8c1e3b7d9f2a5c8e6b1d4f7a3c9e8b5d   (illustrative)

L3 = SHA-256(canonical_json(FindingsEvidence))
   = c4e7b2d9f1a6c8e3b5d7f9a2c4e6b8d1f3a5c7e9b2d4f6a8c1e3b5d7f9a2c4e6   (illustrative)

L4 = SHA-256(canonical_json(DecisionEvidence))
   = f1a3c5e7b9d2f4a6c8e1b3d5f7a9c2e4b6d8f1a3c5e7b9d2f4a6c8e1b3d5f7a9   (illustrative)

L5 = SHA-256(canonical_json(ApprovalEvidence))
   = 9d2f4a6c8e1b3d5f7a9c2e4b6d8f1a3c5e7b9d2f4a6c8e1b3d5f7a9c2e4b6d8f   (illustrative)
```

**Step 2 — pad to an even leaf count.** Five leaves is odd, so the standard convention of
duplicating the last leaf is applied before pairing:

```
L1, L2, L3, L4, L5, L5'   (L5' = L5, duplicated)
```

**Step 3 — build the tree bottom-up, hashing sibling pairs:**

```
Level 1 (leaves):     L1    L2    L3    L4    L5    L5'
                        \   /       \   /       \   /
Level 2 (pairs):     H(L1‖L2)     H(L3‖L4)     H(L5‖L5')
                       = N1          = N2          = N3

N3 is odd-out at level 2 (3 nodes), so it is duplicated: N1, N2, N3, N3'

Level 3:              H(N1‖N2)        H(N3‖N3')
                        = M1             = M2

Level 4 (root):              H(M1‖M2)
                          = merkle_root
                          = 7e4b1d9f2a6c8e3b5d7f1a4c6e9b2d5f8a1c3e6b9d2f4a7c1e5b8d3f6a9c2e4b   (illustrative)
```

**Step 4 — submit.** The `EvidencePackage.merkle_root` above is passed to
`AnchoringProvider.submit_hash(evidence_hash)` (see `docs/06-blockchain/anchoring-providers.md` for
the interface and candidate providers). The provider returns an `anchor_ref` (a transaction hash, a
Constellation snapshot reference, or an ICP canister record id, depending on the provider ultimately
selected per `ADR-007`).

**Step 5 — record the anchor.** A `BlockchainAnchor` (`docs/03-domain/domain-model.md`) is created:

```
BlockchainAnchor {
  id:                  <uuid>
  evidence_package_id: <EvidencePackage.id for D-2026-00842>
  provider:            "constellation_digital_evidence" | "transparency_log"   (ADR-007: Accepted --
                       the chosen adapter and the active fallback, respectively; see
                       anchoring-providers.md §3 for why the EVM L2/ICP candidates weren't built)
  anchor_ref:          <provider-specific reference, illustrative: "0x9a3f...e21b">
  submitted_at:        2026-09-27T14:32:11Z
  proof:               <provider-specific proof payload, opaque outside AnchoringProvider>
}
```

From this point forward, anyone holding a copy of the five canonical evidence payloads (e.g. via a
Decision Passport export) can independently redo Steps 1–3 and compare the result against the
`merkle_root` referenced by this `BlockchainAnchor` — satisfying `BR-EVD-001` — and can independently
call `AnchoringProvider.verify(evidence_hash, proof)` to confirm the anchor itself, without trusting
JuriSense's database (see `docs/06-blockchain/blockchain-purpose.md` and
`docs/06-blockchain/verification.md`).

## 4. Why a Merkle tree rather than one flat hash

Hashing all five evidence items into one flat concatenated hash would also satisfy "one hash proves
the whole package existed," but a Merkle structure is preferred for two reasons that matter to this
product specifically:

- **Selective disclosure.** A future capability (not yet built, but the data structure supports it)
  could let JuriSense prove that a *specific* evidence item (say, the Approval Hash) is part of an
  anchored package, using only that leaf and the sibling hashes along its path (a Merkle proof) —
  without revealing or even needing the other four items. A flat hash offers no such partial proof.
- **Independent recomputability at the item level.** Because each leaf corresponds to exactly one
  `Evidence` record, a verifier reproducing `BR-EVD-001`'s recomputation can diagnose *which*
  category of evidence (contract, policy, findings, decision, approval) fails to match, rather than
  getting an undifferentiated "the package doesn't match" result.

## 5. What never leaves this stage

Only `EvidencePackage.merkle_root` (a 32-byte hash) is ever passed to `AnchoringProvider`. The
canonical JSON payloads, the leaf hashes, and any salts used in canonicalization (see
`docs/06-blockchain/privacy.md`) remain in tenant-isolated internal storage, keyed by
`organization_id` per the tenant-ownership rules in `docs/03-domain/domain-model.md`. This is what
makes `BR-EVD-002` ("no raw contract text, personal data, or confidential document content is ever
included in a `BlockchainAnchor` payload") true by construction rather than by policy alone.
