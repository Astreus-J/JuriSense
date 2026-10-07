# Anchoring Providers — Interface and Candidate Comparison

> Related: `ADR-007` (the accepted decision to abstract the provider behind an interface, and the
> record of the Phase-8 spike this document's final row depends on),
> `docs/06-blockchain/evidence-model.md` (what gets submitted), `docs/06-blockchain/smart-contracts.md`
> (the EVM-path contract sketch and the Constellation/ICP equivalents),
> `docs/09-planning/roadmap.md` (Phase 8).

## 1. The `AnchoringProvider` interface

All blockchain interaction in JuriSense Gate goes through a single interface. No other code in the
product depends on a specific chain SDK, wallet library, or network client — the Compliance Engine,
the Evidence & Audit context, and the verification page all talk only to `AnchoringProvider`
(`ADR-007`). This is what allows the concrete provider decision to remain open (§3) without blocking
any other part of the system.

```
interface AnchoringProvider:

    # Submit a 32-byte evidence hash (an EvidencePackage.merkle_root, never raw content —
    # see docs/06-blockchain/evidence-model.md and docs/06-blockchain/privacy.md) for anchoring.
    # Returns an opaque, provider-specific reference that can later be used to fetch a proof.
    submit_hash(evidence_hash: bytes32) -> anchor_ref: str

    # Given a previously issued anchor_ref, retrieve a provider-specific proof object that
    # attests the hash was anchored at a given time on the underlying network. The internal
    # structure of `proof` is opaque outside the adapter implementation (it may be a Merkle
    # inclusion proof, a block/transaction reference, a canister certificate, etc. — see
    # docs/06-blockchain/smart-contracts.md for what each candidate provider's proof looks like).
    get_proof(anchor_ref: str) -> proof: ProviderProof

    # Independently verify that `evidence_hash` is attested by `proof`, without requiring any
    # JuriSense-internal state. This is the method an external, JuriSense-independent verifier
    # calls — see docs/06-blockchain/verification.md.
    verify(evidence_hash: bytes32, proof: ProviderProof) -> bool
```

Every `BlockchainAnchor` record (`docs/03-domain/domain-model.md`) stores which `provider`
implementation produced it, its `anchor_ref`, and its `proof`, so that different `EvidencePackage`s
anchored under different provider decisions over time remain independently verifiable — switching
the default provider in a future release does not invalidate anchors already issued under a prior
one.

**Implementation** (FEATURE-8.1/8.2): `app.evidence.domain.anchoring.AnchoringProvider` (a
`Protocol`, not an ABC), `AnchorProof`, `AnchorStatus` are this interface in code, unchanged from
the pseudocode above. `app.evidence.application.anchoring_service.get_provider` is the one place
that picks a concrete implementation from `Settings.anchoring_provider`.

## 2. Candidate providers

Per `ADR-007`, research on 2026-09-27 established that the **BLI Legal Tech Hackathon 2 / Legal Hack
2026** (judging 2026-11-05 to 2026-12-05) is sponsored by **ICP (Caffeine AI / DFINITY),
Constellation Network, and Story Protocol** — not Chainlink, which the original mission brief had
assumed. Constellation's own positioning around "immutable anchoring," and its use in a prior
LegalHack for "audit-grade, multi-chain IP records" (combining Story Protocol licensing, ICP escrow,
and Constellation anchoring), made it the closest conceptual match to an evidence-anchoring use case
among the three actual sponsors. Story Protocol itself is not evaluated as an `AnchoringProvider`
candidate: it is an IP-licensing/attribution protocol, not a generic hash-anchoring primitive, and
does not fit the `submit_hash` / `get_proof` / `verify` shape this interface needs.

| | **Constellation Network** | **Generic EVM-compatible L2 testnet** (Base Sepolia or Polygon Amoy) | **ICP / Caffeine AI** |
|---|---|---|---|
| **SDK maturity** | Purpose-built for data anchoring (Hypergraph / Metagraph model); SDK and tooling are less broadly documented outside its own ecosystem than mainstream EVM tooling | Very mature — `viem`/`ethers.js` are the most widely used, best-documented Web3 client libraries in existence; enormous community reference material | Mature for canister development (Motoko/Rust SDK, `dfx` tooling), but "Caffeine AI" specifically is a no-code app-hosting layer whose fit for a narrow "anchor a hash" primitive is less proven |
| **Integration effort estimate** | Unknown until spiked — conceptually the best fit, but the team has no prior hands-on experience with its SDK; effort could range from low (if the anchoring API is as simple as advertised) to high (unfamiliar tooling under hackathon time pressure) | Lowest-risk estimate — a minimal Solidity contract (`docs/06-blockchain/smart-contracts.md`) plus a standard `viem`/`ethers` client is a well-understood pattern the team can implement and test quickly | Unknown until spiked — canister development has its own learning curve (Motoko or Rust + the Internet Computer's async execution model); only preferred if the spike shows unusually low effort |
| **Transaction cost model** | Positioned around free/low-cost data submission on its network (exact current fee model to be confirmed during the spike) | Testnet gas is free (faucet-funded test ETH/MATIC); no real cost during the hackathon, but a production EVM deployment would carry real gas costs per anchor | Reverse-gas model (canister, not caller, pays "cycles"); no per-call cost to the anchoring client once the canister is funded with cycles, but canister cycle top-up is an operational cost to plan for |
| **Proof / verification model** | A third party checks that a hash is included in Constellation's L0 consensus history (snapshot-based inclusion proof) via Constellation's own explorer/API — see `docs/06-blockchain/smart-contracts.md` §Constellation path | A third party reads the `HashAnchored` event (or calls the contract's `verify` view function) directly against a public block explorer (e.g., Basescan/Polygonscan-equivalent for the chosen L2) using only the transaction hash or contract address — no JuriSense involvement needed | A third party queries the canister's public query method (e.g., via the IC's HTTP gateway or `dfx canister call`), optionally checking IC certified variables for tamper-evidence backed by subnet consensus |
| **Fit with hackathon bounty tracks** | Best conceptual fit — Constellation is an actual sponsor with a stated interest in "immutable anchoring" use cases; strongest narrative alignment for a bounty submission | Not a hackathon sponsor track by itself, but the safest technical fallback if Constellation's tooling proves too heavy within the remaining timeline; still demonstrates a real, verifiable Trust Layer | An actual sponsor track (ICP/Caffeine AI), but Caffeine AI's no-code hosting positioning is a comparatively weaker conceptual fit for "anchor a hash and expose a public proof" than either of the other two |

## 3. Final provider selection

**Status: Accepted** (spike concluded 2026-10-07, `ADR-007`, STORY-8.1.1).

**Chosen: Constellation Network, via its Digital Evidence Depository (DED) product** —
`https://de-api.constellationnetwork.io/v1`. This is not the generic Hypergraph/Metagraph path §2
above describes in the abstract; the spike found a purpose-built product for exactly this use case
("create, sign, and submit cryptographic fingerprints for document notarization"), with a
first-party Python SDK (`constellation-digital-evidence-sdk`) and a REST API confirmed live by
hand. `GET /fingerprints/{hash}` requires **no authentication** — confirmed by a direct request
against the production endpoint, which returned the documented 404 JSON shape for an unknown hash.
That single property is what makes the "public, JuriSense-independent" half of
`docs/06-blockchain/verification.md`'s requirement concretely true for this adapter, not just
asserted.

**What the spike actually found, as a real integration-effort result (not positioning):** the SDK
and wire format are low-effort — signing and submission were built and tested end to end against
a mocked transport (`app/evidence/infrastructure/anchoring/constellation_provider.py`,
`tests/evidence/test_anchoring_providers.py`). The blocker is **provisioning, not engineering**:
submission (`POST /fingerprints`) needs an `X-API-Key` plus an `org_id`/`tenant_id` Constellation
issues directly — no self-service signup exists. This is tracked as Plane #198 (request through
the Legal Hack 2026 sponsor channel), not as further spike work.

**Active default until #198 resolves: the transparency-log fallback**
(`docs/09-planning/risks.md` risk 4) — `app.evidence.infrastructure.anchoring.
transparency_log_provider.TransparencyLogAnchoringProvider`. Fully implemented and tested (real
local `git` operations, Ed25519-signed entries), and the one the project ships with today
(`Settings.anchoring_provider` defaults to `"transparency_log"`). Every caller renders this as a
labeled fallback, never as a blockchain anchor — see that module's own docstring for exactly what
"public" still requires (pushing its repo to a public remote, a deliberately separate,
outward-facing step this backend does not perform on its own).

**The EVM L2 and ICP/Caffeine AI candidates were not built.** The spike's own order (Constellation
first) did not need to fall back to them — Constellation's integration effort was low, and its
blocker is a credential handoff the EVM/ICP paths would not avoid either (a funded testnet wallet
and a canister's cycles funding are the same category of "needs something only a human can
provision" blocker). Both remain documented, interface-compatible options (§2,
`docs/06-blockchain/smart-contracts.md`) if Constellation's credentials do not materialize in time.
**Decision artifact:** `ADR-007` (Accepted; full spike findings recorded there).
