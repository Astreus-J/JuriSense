"""Follow-up from H1: `Integration.config`'s credential-like values must be encrypted at
rest in the database, not just masked in API responses (H1 only covered the latter)."""

import uuid

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.integrations.api.schemas import _mask_sensitive
from app.integrations.infrastructure.credential_encryption import (
    CredentialDecryptionError,
    decrypt_integration_config,
    encrypt_integration_config,
)
from app.integrations.infrastructure.repositories import IntegrationRepository
from tests.integrations.test_integration_crud import _admin_headers

CONFIG = {
    "api_key": "sk-live-123",
    "base_url": "https://api.example.com",
    "webhook": {"signing_secret": "whsec-456", "path": "/hooks/docusign"},
    "scopes": ["read", "write"],
}


# ---- Unit level: encrypt_integration_config / decrypt_integration_config ----


def test_encrypt_replaces_only_sensitive_values_with_opaque_tokens() -> None:
    encrypted = encrypt_integration_config(CONFIG)

    assert encrypted["api_key"].startswith("enc:v1:")
    assert encrypted["webhook"]["signing_secret"].startswith("enc:v1:")
    # Non-credential values are untouched, byte for byte.
    assert encrypted["base_url"] == "https://api.example.com"
    assert encrypted["webhook"]["path"] == "/hooks/docusign"
    assert encrypted["scopes"] == ["read", "write"]
    # The plaintext secret never appears anywhere in the stored structure.
    serialized = str(encrypted)
    assert "sk-live-123" not in serialized
    assert "whsec-456" not in serialized


def test_decrypt_reverses_encrypt_exactly() -> None:
    round_tripped = decrypt_integration_config(encrypt_integration_config(CONFIG))

    assert round_tripped == CONFIG


def test_decrypt_passes_through_pre_existing_plaintext_unchanged() -> None:
    """Rows written before this fix shipped have no `enc:v1:` prefix at all -- decrypting
    them must return the original value, not raise, so an upgrade doesn't break every
    integration created before today."""
    legacy_config = {"api_key": "plaintext-from-before-the-fix", "base_url": "https://x.example"}

    assert decrypt_integration_config(legacy_config) == legacy_config


def test_decrypt_raises_on_a_prefixed_value_that_fails_to_decrypt() -> None:
    """QA/security review (2026-10-10): a value that DOES carry the `enc:v1:` prefix but
    fails to decrypt (wrong key after a rotation, or a corrupted/tampered row) must NEVER
    be handed back silently as if it were a real decrypted credential -- that used to be
    indistinguishable from a genuine value to any caller. Covers both a hand-crafted
    non-Fernet string and a real token encrypted under a DIFFERENT key than the one
    currently configured (the actual key-rotation scenario this guards against)."""
    not_a_real_token = {"api_key": "enc:v1:not-actually-a-fernet-token"}
    with pytest.raises(CredentialDecryptionError):
        decrypt_integration_config(not_a_real_token)

    encrypted_under_another_key = {
        "api_key": "enc:v1:" + Fernet(Fernet.generate_key()).encrypt(b'"old-value"').decode()
    }
    with pytest.raises(CredentialDecryptionError):
        decrypt_integration_config(encrypted_under_another_key)


def _changed_top_level_keys(original: dict, transformed: dict) -> set[str]:
    return {key for key in original if original[key] != transformed.get(key)}


def test_masking_and_encryption_cover_the_exact_same_fields() -> None:
    """The whole point of sharing `credential_fields.py` between the H1 masking fix and
    this one: they must never disagree about what's sensitive. Compares which top-level
    keys `_mask_sensitive` (the real masking function, not a re-implementation) actually
    changed against which top-level keys `encrypt_integration_config` actually changed --
    if the two field-matching rules ever drifted apart, this would catch it directly,
    rather than only asserting `is_sensitive_key`'s own opinion of itself."""
    masked_changed = _changed_top_level_keys(CONFIG, _mask_sensitive(CONFIG))
    encrypted_changed = _changed_top_level_keys(CONFIG, encrypt_integration_config(CONFIG))

    assert masked_changed == encrypted_changed == {"api_key", "webhook"}


# ---- Integration level: the stored DB row is actually ciphertext ----


async def test_created_integration_is_stored_encrypted_in_the_database(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await _admin_headers(client, "admin-encrypt-at-rest@example.com")

    created = await client.post(
        "/api/integrations", json={"provider": "docusign", "config": CONFIG}, headers=headers
    )
    assert created.status_code == 201, created.text
    integration_id = created.json()["id"]

    async with db_session_factory() as session:
        row = await IntegrationRepository(session).get_by_id_and_organization(
            uuid.UUID(integration_id), uuid.UUID(created.json()["organization_id"])
        )

    assert row is not None
    assert row.config["api_key"].startswith("enc:v1:")
    assert row.config["webhook"]["signing_secret"].startswith("enc:v1:")
    assert row.config["base_url"] == "https://api.example.com"
    # The actual plaintext secret must never appear in the stored row at all.
    serialized = str(row.config)
    assert "sk-live-123" not in serialized
    assert "whsec-456" not in serialized

    # And it decrypts back to exactly what was submitted -- the seam a future EPIC-9
    # connector will use to get the real credential.
    assert decrypt_integration_config(row.config) == CONFIG


async def test_config_without_credentials_is_stored_unchanged(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    headers = await _admin_headers(client, "admin-encrypt-plain@example.com")
    plain_config = {"channel": "#legal", "retries": 3}

    created = await client.post(
        "/api/integrations", json={"provider": "slack", "config": plain_config}, headers=headers
    )

    async with db_session_factory() as session:
        row = await IntegrationRepository(session).get_by_id_and_organization(
            uuid.UUID(created.json()["id"]), uuid.UUID(created.json()["organization_id"])
        )

    assert row.config == plain_config
