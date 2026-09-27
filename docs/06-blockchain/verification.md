# Public Verification

> Related: `docs/06-blockchain/blockchain-purpose.md` (why this matters), `docs/06-blockchain/evidence-model.md`
> (what is being verified), `docs/06-blockchain/anchoring-providers.md` (the `verify()` method being
> called), `docs/06-blockchain/privacy.md` (what is deliberately withheld),
> `docs/03-domain/business-rules.md` (`BR-EVD-001`, `BR-EVD-002`).

## Purpose

The public verification page exists to answer, for someone who explicitly does **not** want to take
JuriSense's word for it, the single question this entire Trust Layer was built to answer: *does a
specific piece of evidence match what was anchored at decision time, on a public network JuriSense
does not control?* The intended users are external to the deciding organization's trust boundary —
an auditor engaged by the customer, a regulator, a counterparty to the contract in question, or an
acquirer's due-diligence team (`docs/06-blockchain/blockchain-purpose.md`). None of them need a
JuriSense account, need to be logged in, or need to trust anything about JuriSense's servers being
honest or even online at verification time, beyond the initial step of retrieving a reference to
check.

## Verification flow (UX)

1. **Reference input.** The visitor pastes or scans a reference: either a `Decision` id (e.g.,
   `D-2026-00842`, as printed on an exported Decision Passport) or the `EvidencePackage` hash itself
   (the `merkle_root`, as a hex string or embedded in a QR code on the Decision Passport export). No
   login, no organization context, and no search/browse of other decisions is offered — the visitor
   must already hold the specific reference they want to check (this is also a privacy control; see
   `docs/06-blockchain/privacy.md`'s correlation-risk discussion — there is deliberately no public
   directory of anchors to browse).

2. **Resolution.** If a Decision id was given, the system resolves it internally to the
   corresponding `EvidencePackage` and its `merkle_root`. This step alone is *not* the trust-bearing
   part of the flow — it is just a convenience lookup so the visitor doesn't have to already know the
   raw hash. The trust-bearing part is step 4.

3. **Hash display.** The page shows the `merkle_root` hash value in full (e.g.,
   `7e4b1d9f2a6c8e3b5d7f1a4c6e9b2d5f8a1c3e6b9d2f4a7c1e5b8d3f6a9c2e4b`), so the visitor can compare it
   character-for-character against a hash they may have independently recomputed themselves from a
   copy of the original evidence (`BR-EVD-001`, `docs/06-blockchain/evidence-model.md`) — the
   strongest form of the check, since it does not rely on JuriSense's resolution step at all.

4. **Independent on-chain check.** The page calls `AnchoringProvider.get_proof(anchor_ref)` followed
   by `AnchoringProvider.verify(evidence_hash, proof)` (`docs/06-blockchain/anchoring-providers.md`)
   against the network the anchor was actually submitted to, and — just as importantly — surfaces the
   raw, provider-native reference (a transaction hash and block explorer link for an EVM path, a
   Constellation snapshot reference, or an ICP canister/certificate reference — see
   `docs/06-blockchain/smart-contracts.md`) so a sufficiently skeptical visitor can bypass JuriSense's
   UI entirely and query the public ledger or canister directly, using only public infrastructure.
   This is the step that makes the whole page's claim true: the verification does not depend on
   JuriSense's servers being trustworthy, only on the visitor's ability to independently reach the
   underlying network.

5. **Result display.** The page shows one of three outcomes:
   - **Verified** — the hash matches the anchor's proof; displays the anchor's timestamp and the
     network/provider name (e.g., "Anchored 2026-09-27 14:32:11 UTC on Base Sepolia" or the
     equivalent for whichever provider `ADR-007`'s Phase-8 spike selects).
   - **Not found** — no anchor exists for this reference (e.g., a typo, or a reference that predates
     the Trust Layer being enabled).
   - **Mismatch** — the hash exists but does not match what is currently associated with the given
     Decision id, which is precisely the tamper-evidence signal this entire feature exists to
     surface (`docs/06-blockchain/blockchain-purpose.md`).

## What the page deliberately does not reveal

Consistent with the privacy boundary in `docs/06-blockchain/privacy.md` and `BR-EVD-002`, the
verification page's response is limited, by design, to:

- The evidence hash itself (already a non-reversible, salted digest — see
  `docs/06-blockchain/privacy.md`).
- The anchor's timestamp and the network/provider it was anchored on.
- A binary verification status (verified / not found / mismatch).
- The raw provider-native reference needed for the visitor to check independently (a transaction
  hash, snapshot reference, or canister reference — not a payload).

It never reveals:

- Contract content, clause text, or any extracted contractual terms.
- Personal data of any individual involved (approvers, supplier representatives, employees).
- Supplier confidential or financial details.
- Internal policy rule text or rationale beyond the fact that *a* policy version was evaluated.
- Any other `EvidencePackage`s, decisions, or organizations — there is no cross-reference or listing
  capability exposed to an anonymous visitor.

The page's entire value proposition is contained in the sentence it is built to make provably true:
**"this exact evidence hash existed, anchored at this time, on this network"** — and nothing more.
Anyone wanting to confirm what that hash *represents* must already be a party entitled to see the
underlying `EvidencePackage` content (e.g., the customer organization itself, or a party the customer
has shared a Decision Passport export with) — the verification page is not, and is not intended to
be, a way to learn that content from the hash alone.

## Why this satisfies "don't trust JuriSense's database"

Two properties of this flow, taken together, are what make the claim in
`docs/06-blockchain/blockchain-purpose.md` concrete rather than aspirational:

1. The hash comparison in step 3 can be done by a visitor holding an independent copy of the
   original evidence, without using JuriSense's resolution step at all (`BR-EVD-001` makes this
   possible — the `merkle_root` is deterministically recomputable from the `Evidence` set by anyone
   who has it).
2. The proof check in step 4 can be done against the underlying public network directly, using the
   raw reference JuriSense surfaces, without calling back into any JuriSense API or trusting any
   JuriSense-hosted result.

If JuriSense's own servers were compromised, offline, or acting in bad faith, a visitor following
both independent paths above would still reach a correct conclusion about whether the evidence was
altered after the anchor date — which is precisely the property a purely internal audit log cannot
offer (`docs/06-blockchain/blockchain-purpose.md`).
