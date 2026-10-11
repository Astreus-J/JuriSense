"""EVD-002 / BR-EVD-001: the canonical encoding, leaf hash, ordering and tree rules are fixed
(docs/03-domain/evidence.md). Pure-function tests: no database."""

import hashlib
import random

import pytest

from app.evidence.domain.merkle import (
    EMPTY_ROOT,
    LeafInput,
    canonical_json,
    commitment,
    compute_merkle,
    leaf_hash,
)


def _leaf(evidence_type: str, ref_id: str, **payload) -> LeafInput:
    return LeafInput(evidence_type=evidence_type, ref_id=ref_id, payload=payload)


def _node(left: str, right: str) -> str:
    return hashlib.sha256(bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def test_canonical_json_is_sorted_compact_and_ascii() -> None:
    assert canonical_json({"b": 1, "a": "é"}) == b'{"a":"\\u00e9","b":1}'


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})


def test_leaf_hash_ignores_source_key_order() -> None:
    first = LeafInput("rule_evaluation", "r1", {"outcome": "BLOCK", "severity": "HIGH"})
    second = LeafInput("rule_evaluation", "r1", {"severity": "HIGH", "outcome": "BLOCK"})
    assert leaf_hash(first) == leaf_hash(second)


def test_leaf_hash_is_sha256_over_type_ref_and_payload() -> None:
    leaf = LeafInput("document", "doc-1", {"content_hash": "ab"})
    expected = hashlib.sha256(
        b'{"payload":{"content_hash":"ab"},"ref_id":"doc-1","type":"document"}'
    ).hexdigest()
    assert leaf_hash(leaf) == expected


def test_commitment_is_stable_under_key_order() -> None:
    assert commitment({"value": 1, "provenance": {"page": 2}}, "n1") == commitment(
        {"provenance": {"page": 2}, "value": 1}, "n1"
    )


def test_commitment_changes_with_the_nonce() -> None:
    """A different nonce for the same value must produce a different commitment -- otherwise
    salting would do nothing against cross-leaf/cross-package value correlation."""
    assert commitment({"value": True}, "n1") != commitment({"value": True}, "n2")


def test_empty_set_root_is_sha256_of_empty_bytes() -> None:
    assert hashlib.sha256(b"").hexdigest() == EMPTY_ROOT
    assert compute_merkle([]).root == EMPTY_ROOT


def test_single_leaf_root_is_the_leaf_hash() -> None:
    leaf = _leaf("decision", "d1", status="APPROVE")
    assert compute_merkle([leaf]).root == leaf_hash(leaf)


def test_odd_count_duplicates_last_node_per_level() -> None:
    a, b, c = (_leaf("decision", ref, n=i) for i, ref in enumerate("abc"))
    ha, hb, hc = (leaf_hash(x) for x in (a, b, c))
    expected = _node(_node(ha, hb), _node(hc, hc))
    assert compute_merkle([a, b, c]).root == expected


def test_even_count_pairs_without_duplication() -> None:
    leaves = [_leaf("decision", ref, n=i) for i, ref in enumerate("abcd")]
    h = [leaf_hash(x) for x in leaves]
    assert compute_merkle(leaves).root == _node(_node(h[0], h[1]), _node(h[2], h[3]))


def test_ordering_is_by_type_then_ref_id() -> None:
    leaves = [
        _leaf("rule_evaluation", "b", n=0),
        _leaf("decision", "z", n=1),
        _leaf("rule_evaluation", "a", n=2),
    ]
    result = compute_merkle(leaves)
    expected_order = [
        leaf_hash(_leaf("decision", "z", n=1)),
        leaf_hash(_leaf("rule_evaluation", "a", n=2)),
        leaf_hash(_leaf("rule_evaluation", "b", n=0)),
    ]
    assert list(result.ordered_leaf_hashes) == expected_order


def test_same_leaves_in_any_insertion_order_give_identical_root() -> None:
    leaves = [_leaf("policy_version", f"p{i}", version_number=i) for i in range(7)]
    baseline = compute_merkle(leaves).root
    rng = random.Random(7)
    for _ in range(20):
        shuffled = leaves[:]
        rng.shuffle(shuffled)
        assert compute_merkle(shuffled).root == baseline


def test_changing_one_payload_value_changes_the_root() -> None:
    leaves = [_leaf("policy_version", f"p{i}", version_number=i) for i in range(4)]
    original = compute_merkle(leaves).root
    tampered = [*leaves[:3], _leaf("policy_version", "p3", version_number=99)]
    assert compute_merkle(tampered).root != original
