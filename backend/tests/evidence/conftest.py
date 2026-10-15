"""Re-exports the contract/supplier/approval fixtures and helpers the Evidence & Audit tests
drive the real HTTP flows with (mirrors `tests/approvals/conftest.py`'s re-export pattern)."""

from pathlib import Path

import pytest

from app.core.config import get_settings
from tests.approvals.conftest import (  # noqa: F401
    ACTIVE_CNPJ_RESPONSE,
    HIGH_CONFIDENCE_ENVELOPE,
    create_supplier,
    create_user_and_login,
    mock_cnpj_registry,
    mock_openrouter,
    pdf_bytes_with_text,
    register_org_and_login,
    seed_sanctions_index,
)


@pytest.fixture(autouse=True)
def isolated_transparency_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FEATURE-8.1/8.2: every test in this package that submits an anchor goes through the
    real `TransparencyLogAnchoringProvider` (no network, no credentials) by default -- but it
    does real `git` operations, so each test gets its own `tmp_path`-scoped repo and signing
    key instead of writing into the backend's working-directory default
    (`./data/transparency-log`), which would pollute the repo and race across tests that
    otherwise run sequentially today. `monkeypatch.setattr` on the cached `Settings` instance's
    own attributes (not frozen) restores the real default after each test.

    `anchoring_provider` itself is pinned here too (2026-10-15): `backend/.env`'s real runtime
    value switched to `constellation_digital_evidence` once its credentials were live-verified,
    but `Settings` reads that same file as the test suite's own `env_file` -- without this pin,
    `get_provider()` would try the real Constellation DED API in every test here instead of the
    local, credential-free transparency log this package's tests are actually about."""
    settings = get_settings()
    monkeypatch.setattr(settings, "anchoring_provider", "transparency_log")
    monkeypatch.setattr(settings, "transparency_log_repo_path", str(tmp_path / "transparency-log"))
    monkeypatch.setattr(
        settings, "transparency_log_signing_key_path", str(tmp_path / "transparency-log-key")
    )
