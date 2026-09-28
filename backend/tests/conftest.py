from collections.abc import AsyncIterator

import httpx
import pytest
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_session
from app.core.redis import get_redis
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
