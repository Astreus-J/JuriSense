"""The `AnchoringProvider` interface (ADR-007; docs/06-blockchain/anchoring-providers.md §1):
the one abstraction every blockchain/transparency-log integration in the product goes through.
No other code depends on a specific chain SDK, wallet library, or network client -- only this
module's `AnchoringProvider` protocol, `AnchorProof`, and `AnchorStatus`.

Per `BR-EVD-002`/`docs/06-blockchain/privacy.md`: every concrete implementation of
`submit_hash` receives a 32-byte (64-hex-char) `EvidencePackage.merkle_root` and nothing else --
never raw contract/supplier content. This module has no opinion on which network is active;
`app.evidence.application.anchoring_service.get_provider` is the one place that picks a
concrete implementation from config.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class AnchorStatus(StrEnum):
    """Mirrors `BlockchainAnchor`'s lifecycle (docs/03-domain/domain-model.md): `submitted` is
    the state immediately after `submit_hash` returns a reference; a provider whose network
    finalizes asynchronously (Constellation's metagraph consensus) moves to `confirmed` only
    once `get_proof` reports a settled state. `failed` is terminal -- the submission itself was
    rejected or a later confirmation check found it was never finalized."""

    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass(frozen=True)
class AnchorProof:
    """A provider-opaque attestation, in the common shape every call site (the anchoring
    service, the public verification page) needs regardless of which provider produced it.
    `raw` is the provider-native detail (docs/06-blockchain/verification.md step 4's "raw,
    provider-native reference") -- a transaction hash for an EVM path, a Constellation
    fingerprint record, or a git commit's metadata for the transparency-log fallback. Never
    inspected outside the adapter that produced it and the display layer that renders it
    verbatim; no other code branches on its internal shape."""

    status: AnchorStatus
    confirmed_at: str | None
    reference_url: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class AnchoringProvider(Protocol):
    """`docs/06-blockchain/anchoring-providers.md` §1's three methods, verbatim. `provider_name`
    is the value persisted on `BlockchainAnchor.provider` and shown in the Decision Passport /
    public verification page -- see that document's "clearly labeled... not a blockchain
    anchor" requirement for the transparency-log fallback (docs/09-planning/risks.md risk 4)."""

    provider_name: str

    async def submit_hash(self, evidence_hash: str) -> str:
        """Submits a 32-byte hex evidence hash for anchoring. Returns an opaque,
        provider-specific `anchor_ref` usable with `get_proof`."""
        ...

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        """Fetches the current attestation for a previously issued `anchor_ref`."""
        ...

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        """Independently confirms `evidence_hash` is attested by `proof`. `False` for any
        mismatch, any unconfirmed/failed status, or a proof this adapter cannot recognize --
        never raises for a legitimate "not verified" outcome."""
        ...
