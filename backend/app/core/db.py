from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa dos modelos ORM."""


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def task_session() -> AsyncIterator[AsyncSession]:
    """Session for Celery tasks -- **do not** use `get_session()`/`get_sessionmaker()`
    here, even though every existing task did.

    QA review (2026-09-29) found this already failing for real in the suppliers task's
    worker logs: `get_engine()`/`get_sessionmaker()` are `@lru_cache`d, which is correct
    for the FastAPI app (one process, one event loop, for its whole lifetime) but wrong
    for a Celery task -- each task invocation bridges its sync task function to async
    code via a fresh `asyncio.run(...)` call (see e.g. `app.suppliers.infrastructure
    .tasks.run_supplier_check_task`), which creates a **new** event loop every time. An
    `AsyncEngine`'s connection pool binds to whichever loop was running when it first
    created a connection, so the cached engine -- built once, inside whichever task
    happened to run first -- breaks every subsequent task with "Future ... attached to a
    different loop" once its connections are reused from a different loop. Creates and
    disposes a fresh engine scoped to the current (single) event loop on every call
    instead -- more connection-setup overhead per task, but Celery tasks here run one
    background job at a time, not on a latency-sensitive hot path, so that's the right
    trade for actually being correct.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url, echo=settings.database_echo, pool_pre_ping=True
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()
