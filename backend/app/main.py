from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.middleware import MaxBodySizeMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Startup: the engine is created on demand from DATABASE_URL
    yield
    # Shutdown: close the pool's connections
    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # QA/security review (2026-09-29), confirmed live: without this, an oversized
    # upload to /api/contracts/upload was fully received (buffered in memory) before
    # `document_max_size_bytes` was ever checked, inside the route -- see
    # app.core.middleware.MaxBodySizeMiddleware's own docstring. +64KB over the actual
    # document cap for multipart boundaries/headers/other form fields in the same body.
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.document_max_size_bytes + 65_536)

    app.include_router(api_router)
    return app


app = create_app()
