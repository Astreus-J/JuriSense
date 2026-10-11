"""Hash-chaining for `EvidenceOverrideAddendum` (product decision 2026-10-10, closing #187).

`override_decision` (`app/approvals/application/decision_service.py`) can run more than once
against the same Decision while it stays `ACTIVE`, so a package can accumulate more than one
addendum. Each one's `content_hash` commits to its own fields AND the previous addendum's hash
(`previous_hash`, `None` for the first addendum on a package) -- a sequence of overrides is
itself tamper-evident and strictly ordered, not an independent bag of rows. Reuses
`domain/merkle.py`'s `canonical_json` so the exact same encoding rules apply here too.
"""

import hashlib

from app.evidence.domain.merkle import canonical_json


def compute_addendum_hash(
    *,
    evidence_package_id: str,
    decision_id: str,
    sequence_number: int,
    original_status: str,
    new_status: str,
    justification: str,
    overridden_by: str,
    overridden_at: str,
    previous_hash: str | None,
) -> str:
    payload = {
        "evidence_package_id": evidence_package_id,
        "decision_id": decision_id,
        "sequence_number": sequence_number,
        "original_status": original_status,
        "new_status": new_status,
        "justification": justification,
        "overridden_by": overridden_by,
        "overridden_at": overridden_at,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()
