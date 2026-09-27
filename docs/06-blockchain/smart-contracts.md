# On-Chain Anchoring Primitives

> Related: `docs/06-blockchain/anchoring-providers.md` (the `AnchoringProvider` interface and
> candidate comparison), `ADR-007` (provider selection still TBD, Phase-8 spike),
> `docs/06-blockchain/evidence-model.md` (what value gets anchored — always a Merkle root, never
> content).

The `AnchoringProvider` interface (`docs/06-blockchain/anchoring-providers.md`) is intentionally
provider-agnostic. This document describes what sits *behind* that interface for each of the three
candidates under evaluation in `ADR-007`, so that whichever one the Phase-8 spike selects, the
underlying primitive is already understood and documented. In every case the requirement is the
same, deliberately minimal one: **prove that a specific 32-byte hash existed at a specific point in
time, and let anyone check that without JuriSense's involvement.** Nothing about token balances,
ownership transfer, or complex on-chain state is needed, and none is built.

## Path A — Generic EVM-compatible L2 testnet (Base Sepolia or Polygon Amoy)

This is the best-understood path (`docs/06-blockchain/anchoring-providers.md`) and the one with the
most concrete design already sketched. The entire on-chain footprint is a single, small contract.

### Contract sketch

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title HashAnchor
/// @notice Anchors evidence hashes (Merkle roots of a JuriSense EvidencePackage — see
///         docs/06-blockchain/evidence-model.md) with a block timestamp and submitter address.
///         Deliberately minimal: no token, no transferable state, no admin-mutable data.
///         Once a hash is anchored, it is never removed or altered.
contract HashAnchor {

    struct Anchor {
        uint256 timestamp;   // block.timestamp at submission
        address submitter;   // msg.sender at submission
        bool exists;
    }

    // evidence_hash => Anchor. Immutable once set — no function ever overwrites an existing entry.
    mapping(bytes32 => Anchor) private anchors;

    event HashAnchored(bytes32 indexed evidenceHash, uint256 timestamp, address indexed submitter);

    /// @notice Anchor a new evidence hash. Reverts if this exact hash was already anchored,
    ///         since an EvidencePackage's merkle_root is expected to be unique per Decision
    ///         (see BR-EVD-001, docs/03-domain/business-rules.md).
    function anchor(bytes32 evidenceHash) external {
        require(!anchors[evidenceHash].exists, "HashAnchor: already anchored");
        anchors[evidenceHash] = Anchor({
            timestamp: block.timestamp,
            submitter: msg.sender,
            exists: true
        });
        emit HashAnchored(evidenceHash, block.timestamp, msg.sender);
    }

    /// @notice Public, no-trust-required check: does this hash exist on-chain, and since when?
    ///         Any third party can call this directly against the contract — no JuriSense
    ///         backend involvement required (see docs/06-blockchain/verification.md).
    function verify(bytes32 evidenceHash) external view returns (bool exists, uint256 timestamp) {
        Anchor storage a = anchors[evidenceHash];
        return (a.exists, a.timestamp);
    }
}
```

### Mapping to the `AnchoringProvider` interface

- `submit_hash(evidence_hash)` → calls `anchor(evidenceHash)`; the resulting `anchor_ref` is the
  transaction hash (and, once mined, the block number).
- `get_proof(anchor_ref)` → fetches the transaction receipt and the emitted `HashAnchored` event log
  for that transaction; the "proof" is simply the transaction's existence and content on a public
  chain, checkable via any standard JSON-RPC node or block explorer.
- `verify(evidence_hash, proof)` → calls the contract's `verify(evidenceHash)` view function
  directly (no gas cost — it is a read), returning whether the hash is present and its anchored
  timestamp.

### Why this is deliberately minimal

- **No token, no transferable value, no balance logic.** There is nothing here to make this
  contract a financial instrument or a speculative asset — it is a write-once lookup table plus an
  event log, consistent with "Why blockchain is NOT the product" in
  `docs/00-project/overview.md`.
- **No upgradeability, no admin function, no owner.** Nobody — including JuriSense — can alter or
  remove an anchored hash after submission. Immutability is enforced by the contract's own logic
  (the `require(!anchors[...].exists, ...)` guard), not by a promise.
- **Gas cost is bounded and predictable** — one `SSTORE` of a small struct and one event per
  anchor, which is why testnet deployment (free, faucet-funded) is sufficient for the hackathon
  demo, and why a future production deployment's per-anchor cost is easy to estimate.

## Path B — Constellation Network

Constellation does not use a general-purpose smart-contract virtual machine in the same sense as an
EVM chain; its anchoring primitive comes from its own Hypergraph / Metagraph architecture and its L0
consensus layer, which is built specifically around ordering and finalizing data submissions (a
closer conceptual match to "anchor a hash" than to "run arbitrary contract logic"). The equivalent of
the `HashAnchor` contract above is:

- **Submission**: a JuriSense evidence hash is submitted as a data update to a Constellation
  Metagraph (or directly to L0, depending on what the Phase-8 spike finds to be the appropriate
  integration point). Constellation's consensus process orders and finalizes this submission the
  way a block finalizes a transaction on an EVM chain.
- **Proof**: instead of a transaction receipt, the "proof" is Constellation's own snapshot-based
  inclusion proof — evidence that the submitted hash was included in a specific, consensus-finalized
  snapshot at a specific time. This is what `get_proof(anchor_ref)` would return for this adapter.
- **Verification**: a third party checks the inclusion proof against Constellation's public
  explorer/API, independent of JuriSense, in the same spirit as reading an EVM event log from a
  block explorer — the mechanism differs, but the trust property (public, JuriSense-independent,
  consensus-backed existence-at-time-T) is the same.

The exact submission API, proof format, and SDK ergonomics for this path are not yet implemented;
per `ADR-007` and `docs/06-blockchain/anchoring-providers.md`, this is exactly what the Phase-8 spike
will establish before this path can be documented at the same level of concreteness as Path A.

## Path C — ICP / Caffeine AI

On the Internet Computer, the equivalent primitive is a **canister** — a small piece of code plus
its own state, running on an IC subnet — that plays the same role as the `HashAnchor` contract:

- **Submission**: the canister exposes an update method equivalent to `anchor(bytes32 hash)`, which
  stores `(evidence_hash → timestamp, submitter_principal)` in the canister's stable memory. The
  canister's own execution is what plays the role of the EVM's `block.timestamp` — the IC provides a
  consensus-backed time value at the moment the update is processed.
- **Proof**: the IC supports **certified variables** — data a canister can expose with a
  cryptographic certificate, signed by the subnet, that a caller can verify without trusting the
  canister's own honesty (only the IC subnet's consensus). This is the closest ICP equivalent to an
  EVM transaction receipt or a Constellation inclusion proof, and is what `get_proof(anchor_ref)`
  would return for this adapter if certified variables are used.
- **Verification**: a third party calls the canister's public query method (e.g., via `dfx canister
  call` or the IC's HTTP gateway) and, for the strongest guarantee, validates the certificate against
  the IC's public root key — again, no JuriSense backend involvement required.

As with Path B, the concrete canister code, certification approach, and integration effort are not
yet built; `ADR-007` explicitly scopes ICP/Caffeine AI as the third-preference candidate, evaluated
only if the Phase-8 spike shows unusually low integration effort relative to Paths A and B.

## Common ground across all three paths

Regardless of which path the Phase-8 spike selects as the default (`docs/06-blockchain/anchoring-providers.md`
§3, still `TBD`):

- Only a 32-byte hash (the `EvidencePackage.merkle_root`) is ever submitted — never contract text,
  personal data, or any other confidential content (`BR-EVD-002`,
  `docs/06-blockchain/privacy.md`).
- The on-chain/on-canister footprint is a write-once record plus a way to prove when it was written
  — nothing resembling a token, a marketplace, or mutable business state.
- Verification is always possible by a party who trusts only the underlying network (EVM chain,
  Constellation consensus, or IC subnet) — never JuriSense's own database (see
  `docs/06-blockchain/verification.md` and `docs/06-blockchain/blockchain-purpose.md`).
