from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-with-32-bytes-min"  # noqa: S105 -- development only
_DEV_STORAGE_ACCESS_KEY = "test"
_DEV_STORAGE_SECRET_KEY = "test"  # noqa: S105 -- development only (local s3mock S3)


def _normalize_database_url(url: str) -> str:
    """Accept libpq-style URLs (as managed providers hand them out) and
    convert them to SQLAlchemy's asyncpg dialect.

    - postgresql:// -> postgresql+asyncpg://
    - sslmode=... -> ssl=... (asyncpg does not understand sslmode)
    - removes channel_binding (not supported by asyncpg)
    - pooler endpoints (PgBouncer, e.g. Neon's "-pooler") get
      prepared_statement_cache_size=0, required under a transaction pooler
    """
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    if not url.startswith("postgresql+asyncpg://"):
        return url

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    query.pop("channel_binding", None)
    if "-pooler" in (parts.hostname or "") and "prepared_statement_cache_size" not in query:
        query["prepared_statement_cache_size"] = "0"
    return urlunsplit(parts._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "JuriSense API"
    environment: str = "development"
    debug: bool = False

    # External managed database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://jurisense:jurisense@localhost:5432/jurisense"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis on the VPS (cache and queues)
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (S3-compatible): s3mock in dev, Cloudflare R2 in
    # production -- one abstraction, backend swappable via env var (ADR-008
    # addendum -- MinIO, the original dev choice, no longer publishes a
    # freely pullable image). The defaults below are dev-only, matching
    # docker-compose.yml's `s3mock` service; NEVER use these credentials
    # in production.
    storage_endpoint_url: str = "http://localhost:9090"
    storage_access_key: str = _DEV_STORAGE_ACCESS_KEY
    storage_secret_key: str = _DEV_STORAGE_SECRET_KEY
    storage_bucket: str = "jurisense-dev"
    storage_region: str = "us-east-1"

    # CORS: allowed origins (frontend)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Authentication (JWT)
    jwt_secret_key: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Login lockout (5 failed attempts)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Email (SMTP); with no SMTP_HOST configured, emails go to the log (dev)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "JuriSense <no-reply@jurisense.local>"

    # Frontend base URL, used in email links
    frontend_url: str = "http://localhost:3000"

    # Password reset and invitation expiry
    password_reset_expire_minutes: int = 60
    invite_expire_days: int = 7

    @model_validator(mode="after")
    def _normalize_database_url_field(self) -> "Settings":
        self.database_url = _normalize_database_url(self.database_url)
        return self

    @model_validator(mode="after")
    def _require_production_secrets(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret_key == _DEV_JWT_SECRET or len(self.jwt_secret_key) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set in production with at least "
                "32 characters (generate with: openssl rand -hex 32)"
            )
        if self.environment == "production" and (
            self.storage_access_key == _DEV_STORAGE_ACCESS_KEY
            or self.storage_secret_key == _DEV_STORAGE_SECRET_KEY
        ):
            raise ValueError(
                "STORAGE_ACCESS_KEY/STORAGE_SECRET_KEY must be set in production "
                "with real Cloudflare R2 credentials (never the s3mock dev credentials)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
