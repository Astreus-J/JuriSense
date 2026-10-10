"""Encrypts/decrypts credential-like `Integration.config` values at rest (follow-up from
H1's masking fix, which only addressed what the API returns -- storage was unchanged until
this).

Key source (decision, 2026-10-10): a single symmetric Fernet key from `Settings`, the exact
same environment-variable pattern already established for `jwt_secret_key`/
`storage_secret_key` (`docs/04-architecture/security-architecture.md` §4). A managed KMS
(envelope encryption, a wrapped per-row data key, built-in rotation without re-encrypting
data, a decrypt audit trail) was considered and deliberately deferred: no real connector
exists yet to need the plaintext back (EPIC-9 is post-hackathon), and there is no VPS/cloud
account provisioned yet to host one, so it would be new infrastructure with no current
consumer. Revisit if a real enterprise customer's security review requires it (ties into
EPIC-10's "harden multi-tenancy" scope) -- at that point, swap `_fernet()` below for a
KMS-backed unwrap and nothing else in this module's public interface needs to change.
"""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.integrations.domain.credential_fields import transform_sensitive_values

# Versioned so a future key-scheme change (e.g. moving to a KMS-wrapped envelope) can tell
# an old token apart from a new one instead of guessing from shape alone.
_TOKEN_PREFIX = "enc:v1:"


class CredentialDecryptionError(RuntimeError):
    """Raised by `decrypt_integration_config` when a value carries this module's own
    `enc:v1:` prefix but does not decrypt under the current key -- never swallowed, unlike
    a value with no prefix at all (genuine pre-encryption legacy data, passed through)."""


def _fernet() -> Fernet:
    return Fernet(get_settings().integration_credentials_encryption_key.encode())


def _encrypt_value(value: Any) -> str:
    payload = json.dumps(value).encode()
    token = _fernet().encrypt(payload).decode()
    return f"{_TOKEN_PREFIX}{token}"


def _decrypt_value(value: Any) -> Any:
    if not isinstance(value, str) or not value.startswith(_TOKEN_PREFIX):
        # Not a token this module wrote -- e.g. a row written before this fix shipped, or a
        # key this version's detection rule considers sensitive but an earlier one didn't.
        # Returned as-is rather than raising: old data stays readable across the upgrade
        # instead of breaking every existing integration the moment this ships.
        return value
    token = value.removeprefix(_TOKEN_PREFIX)
    try:
        payload = _fernet().decrypt(token.encode())
    except InvalidToken as exc:
        # QA/security review (2026-10-10): a value that DOES carry this module's own prefix
        # but fails to decrypt is a different situation entirely from the legacy-plaintext
        # case above -- it means either the encryption key was rotated without
        # re-encrypting existing rows, or the stored value was corrupted/tampered with.
        # Silently handing back the still-encrypted ciphertext here used to look
        # indistinguishable from a real decrypted value to any caller, which would become a
        # live credential-substitution hazard the moment a real connector (EPIC-9) trusts
        # the result to authenticate outbound. Failing loudly costs nothing today (nothing
        # calls `decrypt_integration_config` yet) and avoids that trap being discovered the
        # hard way later.
        raise CredentialDecryptionError(
            "A stored credential could not be decrypted -- the encryption key may have "
            "been rotated without re-encrypting existing Integration rows, or the stored "
            "value was corrupted."
        ) from exc
    return json.loads(payload)


def encrypt_integration_config(config: dict[str, Any]) -> dict[str, Any]:
    """Called once, right before persisting a new or updated `Integration.config`: every
    credential-like value (by the same key-matching rule the H1 masking fix uses) becomes
    an opaque, prefixed Fernet token; every other field is stored exactly as given."""
    return transform_sensitive_values(config, _encrypt_value)


def decrypt_integration_config(config: dict[str, Any]) -> dict[str, Any]:
    """The reverse -- for the one kind of caller that will eventually need the real
    credential value (a future EPIC-9 connector actually calling out to DocuSign/Slack/
    etc.). Never used by the API response path, which masks instead of decrypting (see
    `api/schemas.py`) -- nothing in this product's request path should ever hand a real
    connector credential back to a browser."""
    return transform_sensitive_values(config, _decrypt_value)
