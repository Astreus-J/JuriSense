# JuriSense Backend

API do JuriSense em Python + FastAPI, gerenciada com [uv](https://docs.astral.sh/uv/).

## Desenvolvimento

```bash
# Instalar dependências (cria .venv automaticamente)
uv sync

# Rodar a API em modo dev (http://localhost:8000)
uv run uvicorn app.main:app --reload

# Testes
uv run pytest

# Lint
uv run ruff check .
```

Documentação interativa da API: `http://localhost:8000/api/docs`
Health check: `GET /api/health`

## Configuração

Copie `.env.example` para `.env` e ajuste as variáveis (banco PostgreSQL externo,
Redis, diretório de documentos por empresa e CORS).

## Docker

```bash
docker build -t jurisense-backend .
docker run -p 8000:8000 --env-file .env jurisense-backend
```

Imagem multi-stage: dependências resolvidas com uv, runtime `python:3.13-slim`
com usuário não-root e apenas o venv + código da aplicação.

## Estrutura

```
app/
  main.py          # create_app, lifespan, middleware
  core/config.py   # Settings (pydantic-settings, lê .env)
  api/router.py    # Router agregador com prefixo /api
  api/routes/      # Rotas por módulo (health, ...)
tests/             # Testes (pytest + httpx ASGITransport)
```

Os Bounded Contexts do DDD (Accounts, Processes, Documents, Deadlines, IA_Services)
serão adicionados como módulos de domínio conforme a implementação avançar.
