# ---- Etapa 0: desenvolvimento (hot reload via docker compose) ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS dev
WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
# libmagic1: python-magic (EPIC-3 upload scanner, SEC-003) loads libmagic via ctypes at
# import time -- missing on every Debian "slim" base image, so app.contracts.infrastructure
# .document_scanner would fail on the very first import (i.e. app startup) without this.
# git: the transparency-log AnchoringProvider (ADR-007, app.evidence.infrastructure.anchoring
# .transparency_log_provider) shells out to the `git` binary to maintain its append-only log.
# This image is also what celery-worker/celery-beat build from (docker-compose.yml, `dev`
# target) -- without it, every evidence.submit_anchor task fails with "git is not installed",
# found via load testing the real stack (2026-10-14), invisible to the test suite since it
# mocks the anchoring provider instead of shelling out for real.
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 git \
    && rm -rf /var/lib/apt/lists/*
EXPOSE 8000
# Código montado como volume pelo compose; uv sync roda no volume do .venv
CMD ["sh", "-c", "uv sync --frozen && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# ---- Etapa 1: build das dependências com uv ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Instala apenas as dependências primeiro (camada cacheável)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Instala o projeto
COPY . .
RUN uv sync --frozen --no-dev

# ---- Etapa 2: runtime enxuto ----
FROM python:3.13-slim-bookworm AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# libmagic1: see the `dev` stage's comment above -- same requirement in production.
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Usuário não-root
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup appuser

# Apenas o venv e o código da aplicação. alembic.ini + alembic/ (migrações) também --
# vivem na raiz do projeto, não dentro de app/, e são obrigatórios para
# `alembic upgrade head` (docker-compose.prod.yml roda isso no boot do container);
# faltando, falha com "FAILED: No 'script_location' key found in configuration"
# (encontrado testando o deploy de produção de verdade, 2026-10-20 -- o estágio `dev`
# nunca pegou essa lacuna porque monta o diretório inteiro como volume).
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/app /app/app
COPY --from=builder --chown=appuser:appgroup /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=appuser:appgroup /app/alembic /app/alembic

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
