"""Canonical encoding and Merkle root for an `EvidencePackage` (EVD-002, BR-EVD-001;
docs/03-domain/evidence.md "How the Merkle root is computed").

This module is the ONE place these rules live. Changing any of them changes every stored
`merkle_root`, so they are a frozen contract, not an implementation detail.

## Canonical JSON
`canonical_json(value)`: UTF-8 bytes (ASCII-only output) of `json.dumps` with sorted keys,
no insignificant whitespace (`separators=(",", ":")`), and `allow_nan=False`. Dict key
order in the source never affects the output.

## Leaf
Each `Evidence` row is one leaf. Its hash is
`sha256(canonical_json({"type": <type>, "ref_id": <ref_id>, "payload": <payload>}))`, as a
lowercase hex string.

## Ordering
Leaves are sorted ascending by `(type, ref_id)` (both `str`, plain Python string order).
`(type, ref_id)` is unique within a package (a database constraint), so there are no ties.

## Tree
Binary SHA-256 tree over the ordered leaf hashes. Each parent is
`sha256(left_bytes || right_bytes)`, where the children are the raw 32-byte digests (not
their hex text). A level with an odd number of nodes duplicates its last node before
pairing. The root of a single leaf is that leaf's hash.

## Empty set
An empty package has root `sha256(b"")` (the hash of the empty byte string).
"""

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

EMPTY_ROOT = hashlib.sha256(b"").hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def commitment(value: Any) -> str:
    """SHA-256 hex digest of a value's canonical JSON. Used for payload fields that must
    commit to content without storing it (contract field values, rationale text, raw
    registry results)."""
    return hashlib.sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class LeafInput:
    evidence_type: str
    ref_id: str
    payload: Mapping[str, Any]


def leaf_hash(leaf: LeafInput) -> str:
    return hashlib.sha256(
        canonical_json(
            {"type": leaf.evidence_type, "ref_id": leaf.ref_id, "payload": dict(leaf.payload)}
        )
    ).hexdigest()


@dataclass(frozen=True)
class MerkleResult:
    root: str
    ordered_leaf_hashes: tuple[str, ...]


def compute_merkle(leaves: Iterable[LeafInput]) -> MerkleResult:
    ordered = sorted(leaves, key=lambda leaf: (leaf.evidence_type, leaf.ref_id))
    hashes = tuple(leaf_hash(leaf) for leaf in ordered)
    return MerkleResult(root=_root_of(list(hashes)), ordered_leaf_hashes=hashes)


def _root_of(hashes: list[str]) -> str:
    if not hashes:
        return EMPTY_ROOT
    level = hashes
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        level = [
            hashlib.sha256(bytes.fromhex(level[i]) + bytes.fromhex(level[i + 1])).hexdigest()
            for i in range(0, len(level), 2)
        ]
    return level[0]
