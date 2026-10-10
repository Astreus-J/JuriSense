"""The shared rule for what counts as a credential-like field in `Integration.config`.

Pure domain logic (no I/O, no external dependencies): both the H1 masking fix
(`api/schemas.py`, API responses) and the at-rest encryption fix
(`infrastructure/credential_encryption.py`, DB storage) apply to exactly this set of
fields, by importing from here rather than each keeping its own copy -- so masking and
encryption can never drift out of sync with each other.
"""

from collections.abc import Callable
from typing import Any

# Matching is by substring on the lowercased key, so over-matching (e.g. "monkey") is the
# accepted trade-off (H1, 2026-10-03).
SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "passwd", "key", "credential", "auth")


def is_sensitive_key(key: str) -> bool:
    return any(fragment in str(key).lower() for fragment in SENSITIVE_KEY_FRAGMENTS)


def transform_sensitive_values(value: Any, transform: Callable[[Any], Any]) -> Any:
    """Walks `value` recursively, applying `transform` to the VALUE of every sensitive-like
    key at any depth, leaving everything else untouched. A sensitive key's value is passed
    to `transform` as a single unit (not recursed into further), whatever its own shape --
    `transform` itself decides how to handle a nested dict/list credential."""
    if isinstance(value, dict):
        return {
            key: (
                transform(item)
                if is_sensitive_key(key)
                else transform_sensitive_values(item, transform)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [transform_sensitive_values(item, transform) for item in value]
    return value
