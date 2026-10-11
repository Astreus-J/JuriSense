"""#187: pure-function tests for the EvidenceOverrideAddendum hash chain
(app/evidence/domain/override_addendum.py). No database."""

from app.evidence.domain.override_addendum import compute_addendum_hash

_BASE_KWARGS = dict(
    evidence_package_id="pkg-1",
    decision_id="dec-1",
    sequence_number=1,
    original_status="BLOCK",
    new_status="APPROVE",
    justification="false positive",
    overridden_by="user-1",
    overridden_at="2026-10-10T00:00:00+00:00",
    previous_hash=None,
)


def test_hash_is_deterministic_for_the_same_inputs() -> None:
    assert compute_addendum_hash(**_BASE_KWARGS) == compute_addendum_hash(**_BASE_KWARGS)


def test_hash_changes_with_previous_hash() -> None:
    first = compute_addendum_hash(**_BASE_KWARGS)
    chained_kwargs = {**_BASE_KWARGS, "sequence_number": 2, "previous_hash": first}
    chained = compute_addendum_hash(**chained_kwargs)
    assert chained != first


def test_hash_changes_if_any_field_changes() -> None:
    baseline = compute_addendum_hash(**_BASE_KWARGS)
    for field, value in (
        ("new_status", "BLOCK"),
        ("justification", "different reason"),
        ("overridden_by", "user-2"),
        ("sequence_number", 2),
    ):
        tampered = compute_addendum_hash(**{**_BASE_KWARGS, field: value})
        assert tampered != baseline, f"changing {field} did not change the hash"
