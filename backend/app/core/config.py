from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-with-32-bytes-min"  # noqa: S105 — apenas desenvolvimento


def _normalizar_database_url(url: str) -> str:
    """Aceita URLs no formato libpq (como provedores gerenciados entregam)
    e converte para o dialeto asyncpg do SQLAlchemy.

    - postgresql:// → postgresql+asyncpg://
    - sslmode=... → ssl=... (asyncpg não conhece sslmode)
    - remove channel_binding (não suportado pelo asyncpg)
    - endpoints com pooler (PgBouncer, ex.: Neon "-pooler") ganham
      prepared_statement_cache_size=0, obrigatório em pool transacional
    """
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    if not url.startswith("postgresql+asyncpg://"):
        return url

    partes = urlsplit(url)
    query = dict(parse_qsl(partes.query))
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    query.pop("channel_binding", None)
    if "-pooler" in (partes.hostname or "") and "prepared_statement_cache_size" not in query:
        query["prepared_statement_cache_size"] = "0"
    return urlunsplit(partes._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "JuriSense API"
    environment: str = "development"
    debug: bool = False

    # Banco de dados gerenciado externo (PostgreSQL)
    database_url: str = "postgresql+asyncpg://jurisense:jurisense@localhost:5432/jurisense"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis na VPS (cache e filas)
    redis_url: str = "redis://localhost:6379/0"

    # Diretório raiz dos documentos por empresa no filesystem da VPS
    documents_root: str = "/dados/empresas"

    # CORS: origens permitidas (frontend)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Autenticação (JWT)
    jwt_secret_key: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Bloqueio de login (RF01: 5 tentativas falhas)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # E-mail (SMTP); sem SMTP_HOST configurado, e-mails vão para o log (dev)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "JuriSense <no-reply@jurisense.local>"

    # URL base do frontend usada nos links de e-mails
    frontend_url: str = "http://localhost:3000"

    # Recuperação de senha (RF02) e convites
    password_reset_expire_minutes: int = 60
    invite_expire_days: int = 7

    @model_validator(mode="after")
    def _ajusta_database_url(self) -> "Settings":
        self.database_url = _normalizar_database_url(self.database_url)
        return self

    @model_validator(mode="after")
    def _exige_segredo_em_producao(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret_key == _DEV_JWT_SECRET or len(self.jwt_secret_key) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY precisa ser definido em produção com ao menos "
                "32 caracteres (gere com: openssl rand -hex 32)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
