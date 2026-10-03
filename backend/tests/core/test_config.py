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


def test_development_does_not_require_any_of_these() -> None:
    Settings(environment="development")


def test_reevaluation_attempt_cap_must_be_at_least_one() -> None:
    """F6: a cap of zero would refuse every re-evaluation and alert on nothing, so it is rejected
    at boot rather than silently disabling the retry path."""
    with pytest.raises(ValidationError):
        Settings(decision_reevaluation_max_attempts=0)
    assert Settings(decision_reevaluation_max_attempts=1).decision_reevaluation_max_attempts == 1
