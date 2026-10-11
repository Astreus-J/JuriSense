import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.approvals.application import approval_service, reevaluation_service
from app.contracts.application import extraction_orchestration
from app.contracts.infrastructure import (
    models as contracts_models,  # noqa: F401 — registers tables on Base
)
from app.core.db import Base, get_session
from app.core.redis import get_redis
from app.evidence.application import anchoring_service, evidence_package_service
from app.evidence.infrastructure import (
    models as evidence_models,  # noqa: F401 — registers tables on Base
)
from app.identity.api.deps import get_email_sender
from app.identity.infrastructure import (
    models as identity_models,  # noqa: F401 — registers tables on Base
)
from app.integrations.infrastructure import (
    models as integrations_models,  # noqa: F401 — registers tables on Base
)
from app.main import app
from app.policies.application import compliance_review_service
from app.policies.infrastructure import (
    models as policies_models,  # noqa: F401 — registers tables on Base
)
from app.suppliers.application import check_service
from app.suppliers.infrastructure import (
    models as suppliers_models,  # noqa: F401 — registers tables on Base
)


class CapturingEmailSender:
    """Captures emails sent during tests."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.messages.append({"to": to, "subject": subject, "body": body})


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
def sent_emails() -> CapturingEmailSender:
    return CapturingEmailSender()


@pytest.fixture(autouse=True)
def stub_supplier_check_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: registering/re-checking a Supplier in a test does not actually run a
    SupplierCheck (no network, no Celery/broker) — mirrors `CapturingEmailSender`'s role
    for email sending. Tests that need a real (mocked-HTTP) check outcome request the
    opt-in `run_supplier_checks_inline` fixture below instead, which overrides this."""

    async def _noop(check_id: object) -> None:
        return None

    monkeypatch.setattr(check_service, "enqueue_supplier_check", _noop)


@pytest.fixture
def run_supplier_checks_inline(
    monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """Opt-in: runs the real `check_service.run_supplier_check` synchronously against the
    test database whenever a check is enqueued, in place of a real Celery worker. Tests
    requesting this fixture must also stub the HTTP layer (see
    `tests/suppliers/conftest.py`'s `mock_cnpj_registry`) — this fixture does not touch
    network access by itself, it only removes the Celery/broker dependency."""

    async def _run_inline(check_id: uuid.UUID) -> None:
        async with db_session_factory() as session:
            await check_service.run_supplier_check(session, check_id=check_id)

    monkeypatch.setattr(check_service, "enqueue_supplier_check", _run_inline)


_ANCHOR_ENQUEUE_CALL_SITES = (compliance_review_service, approval_service, reevaluation_service)


@pytest.fixture(autouse=True)
def stub_anchor_submission_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default (#199): creating/overriding a Decision in a test does not automatically submit
    its EvidencePackage for anchoring (no network, no Celery/broker) — same role as
    `stub_supplier_check_enqueue` above. `POST /evidence-packages/{id}/anchor` is unaffected:
    it calls `anchoring_service.submit_anchor` directly, never through this enqueue seam.

    `enqueue_anchor_submission` is imported by direct name (not module-qualified) at each of
    its three call sites, per the boundary-rule tests' AST-based check -- so unlike
    `stub_supplier_check_enqueue`'s single patch target, this patches all three call-site
    modules' own copies of the name (see `anchoring_service.enqueue_anchor_submission`'s own
    docstring). Tests that need a real auto-submitted anchor to exist request the opt-in
    `submit_anchor_inline` fixture below instead."""

    async def _noop(*, decision_id: object, organization_id: object, actor_id: object) -> None:
        return None

    for module in _ANCHOR_ENQUEUE_CALL_SITES:
        monkeypatch.setattr(module, "enqueue_anchor_submission", _noop)


@pytest.fixture
def submit_anchor_inline(
    monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """Opt-in (#199): runs the real automatic anchor submission synchronously against the
    test database whenever one is enqueued, in place of a real Celery worker. Mirrors
    `run_supplier_checks_inline`'s exact role for its own enqueue seam."""

    async def _run_inline(
        *, decision_id: uuid.UUID, organization_id: uuid.UUID, actor_id: uuid.UUID | None
    ) -> None:
        async with db_session_factory() as session:
            package_view = await evidence_package_service.get_package_for_decision(
                session, organization_id=organization_id, decision_id=decision_id
            )
            await anchoring_service.submit_anchor(
                session,
                organization_id=organization_id,
                evidence_package_id=package_view.package.id,
                actor_id=actor_id,
            )

    for module in _ANCHOR_ENQUEUE_CALL_SITES:
        monkeypatch.setattr(module, "enqueue_anchor_submission", _run_inline)


@pytest.fixture(autouse=True)
def stub_contract_extraction_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: uploading a contract version in a test does not actually run AI
    extraction (no network, no Celery/broker) — same role as
    `stub_supplier_check_enqueue` above. Tests that need a real (mocked-HTTP) extraction
    outcome request the opt-in `run_contract_extraction_inline` fixture instead."""

    async def _noop(contract_version_id: object) -> None:
        return None

    monkeypatch.setattr(extraction_orchestration, "enqueue_contract_extraction", _noop)


@pytest.fixture
def run_contract_extraction_inline(
    monkeypatch: pytest.MonkeyPatch, db_session_factory: async_sessionmaker
) -> None:
    """Opt-in: runs `extraction_orchestration.run_extraction_for_version` synchronously
    against the test database whenever extraction is enqueued, in place of a real Celery
    worker. Tests requesting this fixture must also stub the AI Gateway's HTTP layer
    (see `tests/contracts/conftest.py`'s `mock_openrouter`)."""

    async def _run_inline(contract_version_id: uuid.UUID) -> None:
        async with db_session_factory() as session:
            await extraction_orchestration.run_extraction_for_version(
                session, contract_version_id=contract_version_id
            )

    monkeypatch.setattr(extraction_orchestration, "enqueue_contract_extraction", _run_inline)


@pytest.fixture
async def client(
    db_session_factory: async_sessionmaker, sent_emails: CapturingEmailSender
) -> AsyncIterator[httpx.AsyncClient]:
    async def override_session():
        async with db_session_factory() as session:
            yield session

    fake_redis = FakeAsyncRedis(decode_responses=True)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_email_sender] = lambda: sent_emails

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()
    await fake_redis.aclose()
