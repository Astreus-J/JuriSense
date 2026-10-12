"""Settings' fail-closed production-secret validators (`_require_production_secrets`).

No test previously covered this validator at all -- added while fixing MED-A (security
review): a missing SMTP_HOST in production silently falls back to logging password-reset
and invite tokens instead of emailing them, so `environment=production` must refuse to
boot without one, exactly like it already refuses to boot with a dev JWT/storage secret.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _prod_kwargs(**overrides: object) -> dict:
    base = {
        "environment": "production",
        "jwt_secret_key": "a" * 32,
        "storage_access_key": "real-access-key",
        "storage_secret_key": "real-secret-key",
        "smtp_host": "smtp.example.com",
        "integration_credentials_encryption_key": "tbmho9wV12RQ-6KJU5aaEfSPBkVK9RKZNtMrYnNC6MQ=",
        "openrouter_api_key": "sk-or-v1-real-key",
    }
    base.update(overrides)
    return base


def test_production_boots_with_all_real_secrets() -> None:
    Settings(**_prod_kwargs())


def test_production_refuses_dev_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(**_prod_kwargs(jwt_secret_key="dev-only-insecure-secret-with-32-bytes-min"))


def test_production_refuses_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(**_prod_kwargs(jwt_secret_key="too-short"))


def test_production_refuses_dev_storage_credentials() -> None:
    with pytest.raises(ValidationError, match="STORAGE_ACCESS_KEY"):
        Settings(**_prod_kwargs(storage_access_key="test"))


def test_production_refuses_missing_smtp_host() -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(**_prod_kwargs(smtp_host=None))


def test_production_refuses_dev_integration_credentials_key() -> None:
    with pytest.raises(ValidationError, match="INTEGRATION_CREDENTIALS_ENCRYPTION_KEY"):
        Settings(
            **_prod_kwargs(
                integration_credentials_encryption_key="K8ICvuSzZmFZO1MpA4lBQhyPp8s079pIIZH41eUoU2s="
            )
        )


def test_production_refuses_missing_openrouter_api_key() -> None:
    """#116: without this, the first contract upload in production fails with an opaque
    401 deep inside extraction_service instead of at startup."""
    with pytest.raises(ValidationError, match="OPENROUTER_API_KEY"):
        Settings(**_prod_kwargs(openrouter_api_key=None))


def test_development_does_not_require_any_of_these() -> None:
    Settings(environment="development")


def _constellation_kwargs(**overrides: object) -> dict:
    base = {
        "anchoring_provider": "constellation_digital_evidence",
        "constellation_ded_api_key": "key",
        "constellation_ded_org_id": "org",
        "constellation_ded_tenant_id": "tenant",
        "constellation_ded_private_key": "a" * 64,
    }
    base.update(overrides)
    return base


def test_constellation_provider_boots_with_all_four_credentials_set() -> None:
    Settings(**_constellation_kwargs())


@pytest.mark.parametrize(
    "missing_field",
    [
        "constellation_ded_api_key",
        "constellation_ded_org_id",
        "constellation_ded_tenant_id",
        "constellation_ded_private_key",
    ],
)
def test_constellation_provider_refuses_to_boot_missing_any_one_credential(
    missing_field: str,
) -> None:
    """#116: choosing this provider is itself what makes these required, regardless of
    `environment` -- a dev flipping ANCHORING_PROVIDER to test against the real API with
    an incomplete .env used to fail deep inside the adapter's first real call instead."""
    with pytest.raises(ValidationError, match=missing_field.upper()):
        Settings(**_constellation_kwargs(**{missing_field: None}))


def test_default_transparency_log_provider_does_not_require_constellation_credentials() -> None:
    Settings()  # anchoring_provider defaults to "transparency_log"


def test_reevaluation_attempt_cap_must_be_at_least_one() -> None:
    """F6: a cap of zero would refuse every re-evaluation and alert on nothing, so it is rejected
    at boot rather than silently disabling the retry path."""
    with pytest.raises(ValidationError):
        Settings(decision_reevaluation_max_attempts=0)
    assert Settings(decision_reevaluation_max_attempts=1).decision_reevaluation_max_attempts == 1
