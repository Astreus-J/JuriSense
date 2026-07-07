from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.core.db import get_session
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture(autouse=True)
def _clear_overrides() -> AsyncIterator[None]:
    yield
    app.dependency_overrides.clear()


async def test_health_check(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "jurisense-api"}


async def test_readiness_check_ok(client: httpx.AsyncClient) -> None:
    session = AsyncMock()

    async def fake_session() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_session] = fake_session

    response = await client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    session.execute.assert_awaited_once()


async def test_readiness_check_database_down(client: httpx.AsyncClient) -> None:
    session = AsyncMock()
    session.execute.side_effect = OperationalError("SELECT 1", None, Exception("down"))

    async def fake_session() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_session] = fake_session

    response = await client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}
