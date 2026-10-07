# On-Chain Anchoring Primitives

> Related: `docs/06-blockchain/anchoring-providers.md` (the `AnchoringProvider` interface and
> candidate comparison), `ADR-007` (Accepted: Constellation DED chosen, transparency-log fallback
> active pending Plane #198), `docs/06-blockchain/evidence-model.md` (what value gets anchored —
> always a Merkle root, never content).

The `AnchoringProvider` interface (`docs/06-blockchain/anchoring-providers.md`) is intentionally
provider-agnostic. This document describes what sits *behind* that interface for each candidate the
Phase-8 spike considered — Path B (Constellation) and Path B′ (the transparency-log fallback) are
both built and tested; Paths A and C remain documented, interface-compatible options that were not
needed. In every case the requirement is the same, deliberately minimal one: **prove that a
specific 32-byte hash existed at a specific point in time, and let anyone check that without
JuriSense's involvement.** Nothing about token balances, ownership transfer, or complex on-chain
state is needed, and none is built.

## Path A — Generic EVM-compatible L2 testnet (Base Sepolia or Polygon Amoy)

Not built: the spike reached Constellation first and found it low-effort, so this fallback was not
needed (`ADR-007`). Documented here, at the same level of concreteness as the chosen path, so it
remains a real option if Constellation's credentials (Plane #198) don't materialize. The entire
on-chain footprint would be a single, small contract.

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

## Path B — Constellation Network (chosen, `ADR-007`)

The Phase-8 spike (2026-10-07) found that Constellation does not need the generic Hypergraph/
Metagraph integration this section originally anticipated: **Digital Evidence Depository (DED)**,
a purpose-built notarization product, already exposes exactly the primitive this interface needs,
over plain REST.

- **Submission**: `app.evidence.infrastructure.anchoring.constellation_provider.
  ConstellationAnchoringProvider.submit_hash` signs the evidence hash (as `document_ref`, never
  re-hashed) with the first-party `constellation-digital-evidence-sdk`
  (SECP256K1 signature, RFC 8785 canonical JSON — the SDK's own `SECP256K1_RFC8785_V1` algorithm
  tag) and `POST`s it to `https://de-api.constellationnetwork.io/v1/fingerprints` with an
  `X-API-Key` header. The response's `hash` field is the `anchor_ref`.
- **Proof**: `get_proof(anchor_ref)` calls `GET /fingerprints/{anchor_ref}` — confirmed live,
  **no authentication required**. The response's `status` field
  (`UNASSIGNED|ASSIGNED|FINALIZED_COMMITMENT|ERRORED_COMMITMENT` — the installed SDK's own
  `FingerprintStatus` type, the authoritative vocabulary) maps onto
  `AnchorStatus`: `FINALIZED_COMMITMENT` → `confirmed`, `ERRORED_COMMITMENT` → `failed`, anything
  else → still `submitted`.
- **Verification**: any third party can call the same public `GET /fingerprints/{hash}` endpoint
  directly — no JuriSense backend involvement, exactly `docs/06-blockchain/verification.md`'s
  requirement. `verify(evidence_hash, proof)` is `proof.status == confirmed and proof's
  documentRef == evidence_hash` — **not** the response's `hash` field, which is a distinct,
  server-computed identifier for the whole signed envelope (confirmed from the SDK's own
  `FingerprintDetail` type, which carries both as separate fields).

**Not yet true end to end**: submission requires Constellation-issued credentials (`org_id`/
`tenant_id`/`X-API-Key`) with no self-service signup — tracked as Plane #198, a credential handoff,
not further engineering. Until resolved, Path B′ below is this project's active default.

## Path B′ — Transparency-log fallback (active default, `docs/09-planning/risks.md` risk 4)

Not a blockchain path at all — the documented last-resort if a real chain integration misses the
deadline, and the one the project ships with today while Plane #198 is open.
`app.evidence.infrastructure.anchoring.transparency_log_provider.TransparencyLogAnchoringProvider`:

- **Submission**: signs `{evidence_hash, timestamp}` with an Ed25519 key JuriSense holds (generated
  once, persisted outside the published repo), appends one JSON line to `entries.jsonl` in a local
  git repository, and commits. The `anchor_ref` is the commit SHA.
- **Proof**: reads the entry back from that commit (`git show {sha}:entries.jsonl`) plus the
  commit's own timestamp (`git show -s --format=%aI {sha}`).
- **Verification**: re-checks the Ed25519 signature over `{evidence_hash, timestamp}` against the
  published public key (committed into the repo as `PUBLIC_KEY.txt` the first time it's created) —
  no network call at all for this adapter.

This gives the tamper-evidence property a git history provides (rewriting a past commit changes
every descendant's hash) and a verifiable signature, but **not** third-party, consensus-backed
finality — the repository must still be pushed to a public remote for "anyone can check this
independently" to be concretely true, which this backend deliberately does not do on its own (an
outward-facing action, not a per-request side effect). `provider == "transparency_log"` on every
`BlockchainAnchor` is the non-negotiable signal every caller (Decision Passport, public
verification page) must render as a labeled fallback, never as a blockchain anchor.

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

Not built: `ADR-007`'s spike reached Constellation first, found it low-effort, and did not need to
evaluate ICP/Caffeine AI as its own "unusually low integration effort" escape hatch required. This
path remains documented and interface-compatible if that changes.

## Common ground across every path

Regardless of which `AnchoringProvider` is active (`docs/06-blockchain/anchoring-providers.md` §3,
Accepted):

- Only a 32-byte hash (the `EvidencePackage.merkle_root`) is ever submitted — never contract text,
  personal data, or any other confidential content (`BR-EVD-002`,
  `docs/06-blockchain/privacy.md`).
- The on-chain/on-canister footprint is a write-once record plus a way to prove when it was written
  — nothing resembling a token, a marketplace, or mutable business state.
- Verification is always possible by a party who trusts only the underlying network (EVM chain,
  Constellation consensus, or IC subnet) — never JuriSense's own database (see
  `docs/06-blockchain/verification.md` and `docs/06-blockchain/blockchain-purpose.md`).
