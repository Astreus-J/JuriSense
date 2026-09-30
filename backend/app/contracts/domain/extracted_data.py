"""Pure helpers for walking a `ContractVersion.extracted_data` dict -- the persisted form
of `app.ai_services.domain.schema.ContractFields` (JSON, so plain dicts/lists, not the
Pydantic model itself). Shared by the confidence gate (BR-CON-003) and the human
confirmation endpoint (CON-005) so both agree on exactly what counts as "a field."

A "field leaf" is any dict shaped like an `ExtractedValue`
(`docs/05-ai/structured-extraction.md`): it has `value`/`confidence`/`provenance` keys.
"""

from typing import Any

_LEAF_KEYS = {"value", "confidence", "provenance"}


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and _LEAF_KEYS.issubset(node.keys())


def iter_field_leaves(fields: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every `ExtractedValue`-shaped leaf in `fields`, as `(dotted_path, leaf_dict)`
    pairs. `leaf_dict` is the actual nested dict object (not a copy) so callers may
    mutate it in place (see `mark_confirmed` below)."""
    found: list[tuple[str, dict[str, Any]]] = []

    def _walk(node: Any, path: str) -> None:
        if _is_leaf(node):
            found.append((path, node))
            return
        if isinstance(node, dict):
            for key, value in node.items():
                _walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(fields, "")
    return found


def min_confidence(fields: dict[str, Any]) -> float:
    """BR-CON-003 / contract-compliance.md: the minimum across every extracted field,
    never an average -- one weak field must not be masked by unrelated high-confidence
    fields. No fields at all is treated as the least-confident case (0.0), consistent
    with evaluation.md's "lean toward under-confidence" safety philosophy."""
    leaves = iter_field_leaves(fields)
    if not leaves:
        return 0.0
    return min(leaf["confidence"] for _, leaf in leaves)


def low_confidence_paths(fields: dict[str, Any], *, threshold: float) -> list[str]:
    return [
        path
        for path, leaf in iter_field_leaves(fields)
        if leaf["confidence"] < threshold and not leaf.get("human_confirmed", False)
    ]


def apply_confirmation(
    fields: dict[str, Any], *, corrections: dict[str, Any], threshold: float
) -> dict[str, Any]:
    """CON-005/BR-CON-003: for every field currently below `threshold`, either apply the
    human's corrected `value` (from `corrections`, keyed by the same dotted path
    `iter_field_leaves` produces) or, if no correction was given for that path, accept
    the AI-extracted value as human-confirmed as-is. Either way the leaf is stamped
    `human_confirmed: true` -- "recorded as human-confirmed... preserving an honest
    provenance trail" (contract-compliance.md), never silently promoted to look like a
    high-confidence AI extraction (the original `confidence` value is left untouched).

    Mutates and returns the same `fields` dict (callers pass a copy if they need the
    pre-confirmation version preserved).
    """
    for path, leaf in iter_field_leaves(fields):
        if leaf["confidence"] >= threshold:
            continue
        if path in corrections:
            leaf["value"] = corrections[path]
            leaf["human_corrected"] = True
        leaf["human_confirmed"] = True
    return fields
