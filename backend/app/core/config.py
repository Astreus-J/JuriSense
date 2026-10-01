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

    # AI Gateway (ADR-005 + docs/adr/ADR-005-addendum-interim-ai-provider.md): interim
    # provider is OpenRouter, an OpenAI-compatible API, until a real OpenAI/Anthropic key
    # exists -- swapping to a real provider is a config-only change (base URL + key +
    # model names), never an application-code change.
    ai_gateway_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str | None = None
    ai_extraction_primary_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    ai_extraction_fallback_model: str = "qwen/qwen3.8-27b:free"
    ai_extraction_timeout_seconds: float = 60.0
    # Contracts routinely exceed a single extraction call's practical input budget for
    # very long master service agreements; full structural chunking
    # (docs/05-ai/document-intelligence.md "Chunking strategy") is out of scope for this
    # phase -- text is truncated to this budget and a warning is logged, documented here
    # rather than silently dropped. Revisit once chunking is implemented.
    ai_extraction_max_input_chars: int = 60_000

    # BR-CON-003's confidence threshold, resolved here per the same "pick a defensible
    # default now, document it, revisit after real data" approach used for ADR-008/
    # ADR-017's TBDs -- see docs/05-ai/evaluation.md's addendum note and
    # docs/adr/ADR-005-addendum-interim-ai-provider.md. A per-field minimum, not a
    # document-level average (contract-compliance.md), in the 0.80-0.85 candidate range
    # that document names; 0.82 is the chosen starting point pending golden-dataset
    # calibration. Configurable per environment, not a hardcoded constant, precisely
    # because it is expected to move once real extraction data exists.
    contract_extraction_confidence_threshold: float = 0.82

    # SEC-003: upload validation limits (see app/contracts/infrastructure/document_scanner.py
    # for the full malware/type-spoofing scope decision).
    document_max_size_bytes: int = 25_000_000  # 25 MB

    # BR-APR-003's SLA duration is an explicit `TBD` pending customer discovery
    # (docs/03-domain/approvals.md "SLA and escalation") -- a flat 48h (2 "business
    # days", treated as flat wall-clock time rather than real business-day calendar
    # arithmetic, which is out of scope this round) is the documented hackathon default.
    approval_request_sla_hours: int = 48

    # A Decision's `valid_until` duration is likewise a documented `TBD` (BR-DEC-004
    # doesn't pin a number) -- 90 days is a plain, defensible default pending real data.
    decision_valid_days: int = 90

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
        if self.environment == "production" and not self.smtp_host:
            # Found in security review (MED-A): with no smtp_host, email sending
            # silently falls back to ConsoleEmailSender, which logs the full
            # email body -- including raw password-reset and invite links, i.e.
            # a bearer-equivalent opaque token -- via logger.info(). A
            # misconfigured production deploy would ship those tokens into the
            # application log stream instead of failing to boot.
            raise ValueError(
                "SMTP_HOST must be set in production -- without it, password-reset "
                "and invite links are written to the application log instead of emailed"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
