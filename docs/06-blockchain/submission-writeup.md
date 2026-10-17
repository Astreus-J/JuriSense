# Blockchain Integration — Submission Write-up

> Audience: hackathon judges and sponsor-bounty reviewers. This is the focused, judge-facing version
> of the material in `docs/06-blockchain/` — written to be read standalone (on the BUIDL page or
> linked from it), without requiring a judge to read the full architecture tree first. Full detail
> and sourcing: `docs/06-blockchain/blockchain-purpose.md`, `anchoring-providers.md`,
> `evidence-model.md`, `privacy.md`, `verification.md`, and `docs/adr/ADR-007-blockchain-anchoring-provider.md`.

## What problem the blockchain layer solves

JuriSense Gate is a compliance product. Its core promise is: "here is proof this vendor decision was
actually reviewed, on this date, against the policy in force at the time." An internal database can
make that claim — but only to someone willing to trust JuriSense's own systems to report on
themselves. The parties who most need to ask "prove it" (auditors, regulators, an acquirer's
due-diligence team, opposing counsel in a dispute) are structurally the least willing to accept
"trust us" as an answer.

JuriSense Gate anchors a hash of every Decision's Evidence Package on a public, tamper-evident
network so that an **external, JuriSense-independent party** can check — months or years later,
without ever needing API access to JuriSense — whether that evidence was altered after the decision
was made. That is the entire scope of the blockchain component. No token, no NFT, no DAO, and no
document or personal data ever goes on-chain.

## The interface: `AnchoringProvider`

All blockchain interaction in the product goes through one interface — no other code depends on a
specific chain SDK:

```
interface AnchoringProvider:
    submit_hash(evidence_hash: bytes32) -> anchor_ref: str
    get_proof(anchor_ref: str) -> proof: ProviderProof
    verify(evidence_hash: bytes32, proof: ProviderProof) -> bool
```

This was a deliberate architecture decision (`ADR-007`), made before any specific provider was
chosen, so the product would never be hard-locked to one chain's roadmap. Two adapters implement it
today, fully interchangeable behind the same interface and the same `Settings.anchoring_provider`
config value:

- **Constellation Network, via its Digital Evidence Depository (DED) product** — the active provider
  (see below).
- **A transparency-log fallback** — real local `git` operations with Ed25519-signed entries, used if
  the primary provider is ever unreachable. Every caller in the product renders this as a labeled
  fallback, never as a blockchain anchor, regardless of which one is active — this labeling rule is
  non-negotiable (`docs/09-planning/risks.md` risk 4).

## What was actually built, and verified live — not just implemented

Constellation DED was chosen after a technical spike (`ADR-007`, STORY-8.1.1) found it to be a
purpose-built product for exactly this use case ("create, sign, and submit cryptographic fingerprints
for document notarization"), with a first-party Python SDK and a public REST API that requires **no
authentication to verify an anchor** — `GET /fingerprints/{hash}` is callable by anyone, which is what
makes "a third party can verify without any JuriSense involvement" concretely true rather than merely
asserted.

Credentials were provisioned 2026-10-12. On 2026-10-15, `ANCHORING_PROVIDER` was switched from the
fallback to `constellation_digital_evidence` and the integration was verified against the real
network, not a mock: a real compliance `Decision`'s anchor submission called the live Constellation
API (`POST /fingerprints` → `200`), and a follow-up `GET` on that same fingerprint returned
`"status": "FINALIZED_COMMITMENT"` with a real `batchGlobalSnapshotHash` and
`batchMetagraphSnapshotHash` — genuine inclusion in Constellation's snapshot-based consensus, not
just acceptance into an internal queue. Full detail: `ADR-007`'s 2026-10-15 addendum.

This is a runtime configuration value, not a permanent fact — it can be reconfirmed live at any time
by anyone with access to the API, and the team does so before any live demo or presentation rather
than asserting it from memory.

## What exactly gets anchored

Only the **Merkle root hash** of a Decision's Evidence Package (`EvidencePackage.merkle_root`) —
never the underlying contract, never personal data, never any business-sensitive content. The
Evidence Package is built from the full set of evidence behind a compliance decision (the AI
extraction result and its citations, the policy version and rule evaluations, the approval record);
its Merkle root is deterministically recomputable from that evidence set at any time
(`BR-EVD-001`). That is what makes independent verification possible: anyone holding the original
evidence (e.g., via a Decision Passport export) can recompute the same root JuriSense computed and
compare it to what is anchored on-chain, without taking JuriSense's word for anything.

## How a third party verifies an anchor independently

1. Obtain the Evidence Package (e.g., from a Decision Passport export) and recompute its Merkle root.
2. Call `AnchoringProvider.verify(evidence_hash, proof)` — or, for Constellation DED specifically,
   query `GET https://de-api.constellationnetwork.io/v1/fingerprints/{hash}` directly, with no
   authentication and no JuriSense API involved at all.
3. Compare the recomputed hash against what the network attests. A mismatch proves tampering after
   the anchor date; a match proves the evidence is unaltered since that point — provably, using only
   public information.

The product's own public verification page (`frontend/src/app/verify/page.tsx`, rate-limited,
anonymous) performs this same check for convenience, but it is not required — the check is designed
to work entirely without it.

## What blockchain does, and precisely does not, prove

This is a trust-*minimization* claim, not a trust-*elimination* claim:

- **Proves**: that a specific hash existed, unaltered, as of a specific point in time attested to by a
  network JuriSense does not control. Tampering after that point is provably detectable by anyone.
- **Does not prove**: that the underlying evidence was accurate, complete, or fairly evaluated. That
  is the job of the AI extraction, the Policy Engine, and the human approval workflow — the Trust
  Layer's job starts exactly where those end. JuriSense Gate does not claim to eliminate legal risk;
  it makes the decision process systematic and evidenced.

## A note on sponsor/bounty fit

Earlier project documentation (written before the live hackathon page could be checked) assumed this
edition's bounty sponsors were ICP, Constellation Network, and Story Protocol. The live page, checked
directly on 2026-10-16, shows this edition's actual bounties are **Chainlink** and **RYO-CHAN** —
neither Constellation, ICP, nor Story Protocol currently has a bounty track here. The team's decision
is to keep the Constellation DED integration as built: it is a genuinely sound, independently
verifiable implementation of the `AnchoringProvider` abstraction on its own technical merits, already
live-verified end to end, and the `AnchoringProvider` interface itself was built sponsor-agnostic by
design specifically so the product's architecture would never depend on guessing a sponsor list
correctly. Full correction: `docs/adr/ADR-007-blockchain-anchoring-provider.md`'s 2026-10-16 addendum.
