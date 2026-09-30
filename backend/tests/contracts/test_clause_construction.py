"""BR-CON-004/CON-004: a `Clause` without a page/span citation cannot be constructed at
all -- tested here at construction time directly (not just via the API), per this
epic's explicit instruction not to only test the nullable-column-plus-later-validation
shape.
"""

import uuid

import pytest

from app.contracts.domain.errors import InvalidClauseProvenanceError
from app.contracts.infrastructure.models import Clause

_VERSION_ID = uuid.uuid4()


def _make(**overrides: object) -> Clause:
    kwargs = {
        "contract_version_id": _VERSION_ID,
        "clause_type": "liability",
        "page": 3,
        "text_span": {"start": 10, "end": 50},
        "confidence": 0.9,
    }
    kwargs.update(overrides)
    return Clause(**kwargs)


def test_valid_clause_constructs_successfully() -> None:
    clause = _make()
    assert clause.page == 3
    assert clause.text_span == {"start": 10, "end": 50}


def test_missing_page_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(page=None)


def test_missing_text_span_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(text_span=None)


def test_text_span_missing_start_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(text_span={"end": 50})


def test_text_span_null_start_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(text_span={"start": None, "end": 50})


def test_page_zero_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(page=0)


def test_negative_page_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(page=-1)


def test_text_span_end_before_start_rejected_at_construction() -> None:
    with pytest.raises(InvalidClauseProvenanceError):
        _make(text_span={"start": 50, "end": 10})


def test_boolean_page_rejected_at_construction() -> None:
    """`bool` is a subclass of `int` in Python -- guard against `page=True` sneaking
    past an `isinstance(page, int)` check."""
    with pytest.raises(InvalidClauseProvenanceError):
        _make(page=True)
