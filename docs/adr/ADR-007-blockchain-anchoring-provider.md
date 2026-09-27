# ADR-007 — Blockchain Anchoring Provider Abstraction

## Status
Proposed — pending technical spike (Phase 8 of the roadmap)

## Context
The mission brief originally assumed Chainlink as the blockchain partner. Research on 2026-09-27
found that the **BLI Legal Tech Hackathon 2 / Legal Hack 2026** (judging 2026-11-05 to 2026-12-05,
awards 2026-12-12) is sponsored by **ICP (Caffeine AI / DFINITY), Constellation Network, and Story
Protocol** — Chainlink was not found among sponsors or bounty partners for this edition.
Constellation's positioning ("immutable anchoring," used in the prior LegalHack for "audit-grade,
multi-chain IP records") is a close conceptual match to JuriSense Gate's Evidence Package /
Decision Passport anchoring need. The user decided (2026-09-27) that the Trust Layer must not be
hard-locked to a single network.

## Decision
Define an **`AnchoringProvider` interface** in `06-blockchain/anchoring-providers.md`:
`submit_hash(evidence_hash) -> anchor_ref`, `get_proof(anchor_ref) -> proof`,
`verify(evidence_hash, proof) -> bool`. All blockchain interaction in the product goes through this
interface; no other code depends on a specific chain SDK. Only **hashes** (Merkle roots of the
Evidence Package) are ever submitted on-chain — never raw contract/supplier data (see
`06-blockchain/privacy.md`).

## Resolution
A technical spike during **Phase 8** will implement and benchmark at least one concrete adapter and
pick the default for the hackathon demo, evaluating: SDK maturity, integration effort within the
remaining timeline, transaction cost, and fit with the hackathon's actual bounty tracks.

**Current preferred candidates** (in order): (1) **Constellation Network** — best conceptual fit
and real hackathon sponsor; (2) a generic **EVM-compatible L2 testnet** (Base Sepolia or Polygon
Amoy) — safest fallback if Constellation's SDK/tooling proves too heavy for the remaining timeline,
since EVM tooling (viem/ethers + a minimal hash-anchoring contract) is the best-understood path;
(3) **ICP/Caffeine AI** — evaluated only if the spike shows unusually low integration effort, since
its positioning (no-code app hosting) is a weaker fit for "anchor a hash and expose a public proof"
than Constellation or a plain EVM contract.

This ADR's status moves to Accepted once the spike concludes; the choice does not change the
`AnchoringProvider` interface or anything above it in the stack.

## Alternatives Considered
- **Hard-commit to Chainlink now** (original brief): rejected — not a sponsor of this hackathon
  edition, and locking to one chain before validating integration effort risks the hackathon
  deadline for no confirmed benefit. Chainlink CRE/Data Feeds/Functions remain a legitimate future
  `AnchoringProvider` adapter if a customer/partnership reason emerges later.
- **No blockchain component**: rejected by explicit product requirement (Trust Layer is core to the
  Decision Passport's value proposition and to the hackathon's blockchain-track fit).

## Consequences
- Hackathon narrative and product architecture stay decoupled from any single sponsor's roadmap.
- `06-blockchain/*` documents the abstraction and privacy model now; the concrete adapter choice is
  explicitly deferred and tracked, not silently assumed.
