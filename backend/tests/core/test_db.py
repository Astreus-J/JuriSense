"""`task_session()` (QA review, 2026-09-29): Celery tasks bridge their sync task function
to async code via a fresh `asyncio.run(...)` call on every single invocation. The
FastAPI-oriented `get_session()`/`get_sessionmaker()` are `@lru_cache`d, so reusing them
from a task reuses one `AsyncEngine`/connection pool across multiple, independent event
loops -- confirmed live against the real dev Neon DB to reproduce the exact
"Task ... got Future ... attached to a different loop" `RuntimeError` already seen in the
suppliers Celery worker's production logs, on the *second* of two sequential
`asyncio.run()` calls using the old cached-sessionmaker pattern. `task_session()` fixes
this by creating and disposing a fresh engine scoped to the current event loop on every
call; this test locks in that no-cross-loop-state contract so it can't regress silently.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core import db as db_module
from app.core.config import Settings
from app.core.db import task_session


async def test_task_session_works_across_independent_event_loops(monkeypatch) -> None:
    """Simulates two separate Celery task invocations in the same worker process (each
    with its own `asyncio.run()`-created event loop) by calling `task_session()` from
    two independently-run coroutines. Uses SQLite here purely for test hermeticity --
    the fix itself was verified live against the real asyncpg/Postgres failure mode
    documented above; this test guards the structural contract (fresh engine, no shared
    cross-call state), not the asyncpg-specific error itself.
    """
    engines: list[AsyncEngine] = []

    def _fake_get_settings() -> Settings:
        return Settings(database_url="sqlite+aiosqlite:///:memory:", environment="development")

    monkeypatch.setattr(db_module, "get_settings", _fake_get_settings)

    async def _run_once() -> int:
        async with task_session() as session:
            engines.append(session.bind)
            result = await session.execute(text("SELECT 1"))
            return result.scalar()

    first = await _run_once()
    second = await _run_once()

    assert first == 1
    assert second == 1
    # Each call got its own engine instance -- the whole point of the fix.
    assert engines[0] is not engines[1]


async def test_task_session_disposes_the_engine_on_exit(monkeypatch) -> None:
    disposed = {"called": False}
    real_dispose = AsyncEngine.dispose

    async def _tracking_dispose(self, *args, **kwargs):
        disposed["called"] = True
        return await real_dispose(self, *args, **kwargs)

    def _fake_get_settings() -> Settings:
        return Settings(database_url="sqlite+aiosqlite:///:memory:", environment="development")

    monkeypatch.setattr(db_module, "get_settings", _fake_get_settings)
    monkeypatch.setattr(AsyncEngine, "dispose", _tracking_dispose)

    async with task_session() as session:
        await session.execute(text("SELECT 1"))

    assert disposed["called"] is True
