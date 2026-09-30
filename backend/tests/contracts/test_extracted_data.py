"""BR-CON-003's confidence gate is a per-field minimum, never an average (contract-
compliance.md) -- and CON-005's confirmation must stamp `human_confirmed` without
silently rewriting the original AI confidence."""

from app.contracts.domain.extracted_data import (
    apply_confirmation,
    iter_field_leaves,
    low_confidence_paths,
    min_confidence,
)

_PROVENANCE = {"document_id": "doc-1", "page": 1, "text_span": {"start": 0, "end": 5}}


def _leaf(confidence: float, value: object = "x") -> dict:
    return {"value": value, "confidence": confidence, "provenance": _PROVENANCE}


def test_min_confidence_is_the_minimum_not_the_average() -> None:
    fields = {
        "contract_type": _leaf(0.99),
        "liability": {"type": _leaf(0.55), "cap": _leaf(0.98)},
    }
    assert min_confidence(fields) == 0.55


def test_min_confidence_with_no_fields_is_zero() -> None:
    assert min_confidence({}) == 0.0


def test_iter_field_leaves_walks_nested_dicts_and_lists() -> None:
    fields = {
        "obligations": [_leaf(0.7), _leaf(0.8)],
        "liability": {"type": _leaf(0.9)},
    }
    paths = {path for path, _ in iter_field_leaves(fields)}
    assert paths == {"obligations[0]", "obligations[1]", "liability.type"}


def test_low_confidence_paths_excludes_already_confirmed() -> None:
    fields = {
        "a": _leaf(0.5),
        "b": {**_leaf(0.4), "human_confirmed": True},
    }
    assert low_confidence_paths(fields, threshold=0.8) == ["a"]


def test_apply_confirmation_accepts_as_is_when_no_correction_given() -> None:
    fields = {"liability": {"type": _leaf(0.5, value="unlimited")}}
    apply_confirmation(fields, corrections={}, threshold=0.8)
    leaf = fields["liability"]["type"]
    assert leaf["human_confirmed"] is True
    assert leaf["value"] == "unlimited"  # unchanged
    assert leaf["confidence"] == 0.5  # never silently bumped
    assert "human_corrected" not in leaf


def test_apply_confirmation_applies_a_correction() -> None:
    fields = {"liability": {"type": _leaf(0.5, value="unlimited")}}
    apply_confirmation(fields, corrections={"liability.type": "capped"}, threshold=0.8)
    leaf = fields["liability"]["type"]
    assert leaf["value"] == "capped"
    assert leaf["human_confirmed"] is True
    assert leaf["human_corrected"] is True
    assert leaf["confidence"] == 0.5  # the original AI confidence is preserved, not rewritten


def test_apply_confirmation_leaves_high_confidence_fields_untouched() -> None:
    fields = {"contract_type": _leaf(0.95, value="nda")}
    apply_confirmation(fields, corrections={}, threshold=0.8)
    leaf = fields["contract_type"]
    assert "human_confirmed" not in leaf
