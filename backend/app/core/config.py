from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-with-32-bytes-min"  # noqa: S105 -- development only
_DEV_STORAGE_ACCESS_KEY = "test"
_DEV_STORAGE_SECRET_KEY = "test"  # noqa: S105 -- development only (local s3mock S3)
# A real (correctly-formatted) Fernet key, but publicly known from being committed here --
# development only, same trust level as _DEV_JWT_SECRET. Generate a real one for production
# with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_DEV_INTEGRATION_CREDENTIALS_KEY = "K8ICvuSzZmFZO1MpA4lBQhyPp8s079pIIZH41eUoU2s="  # noqa: S105


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

    # Rate limiting (docs/07-engineering/security.md "Rate limiting on public endpoints").
    # #112: per-IP, on the one genuinely unauthenticated route (GET /public/verify) -- tuned
    # to allow a human re-checking a hash a few times, not an enumeration/scraping script.
    public_verification_rate_limit_max_requests: int = 30
    public_verification_rate_limit_window_seconds: int = 60
    # #143: per-organization, on authenticated routes that trigger a real external API call
    # and/or a Celery task (confirmed via load test: 15 back-to-back POST /suppliers/{id}/
    # recheck calls all returned 202 with no throttling) -- a coarser abuse/cost backstop,
    # separate from plan-limit enforcement (ADR-014, BR-ORG-003), which governs business
    # limits, not abuse.
    external_call_rate_limit_max_requests: int = 10
    external_call_rate_limit_window_seconds: int = 60

    # Integration connector credentials at rest (STORY: encrypt integration connector
    # credentials at rest). Environment-variable key, same pattern as jwt_secret_key/
    # storage_secret_key above (docs/04-architecture/security-architecture.md §4) --
    # deliberately not a managed KMS: no real connector exists yet (EPIC-9 is
    # post-hackathon) and no VPS/cloud account is provisioned yet to host one. Revisit if a
    # real enterprise customer's security review requires it (ties into EPIC-10).
    integration_credentials_encryption_key: str = _DEV_INTEGRATION_CREDENTIALS_KEY

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

    # #180 (security finding POL-004): per-organization resource-exhaustion backstop --
    # unbounded Policies/PolicyVersions/Rules is an unbounded Rule-evaluation cost lever,
    # since every currently-published PolicyVersion's Rules are pooled into every
    # trigger_review/simulate call. Generous enough to never bother a real customer;
    # matches SimulateRequest.contract_version_ids' own max_length=50 cap's precedent of
    # "a config-driven ceiling, not an unbounded resource."
    max_policies_per_organization: int = 100
    max_policy_versions_per_policy: int = 50
    max_rules_per_policy_version: int = 200
    # #120/security review (2026-10-12): same POL-004 backstop, scoped per Rule -- unlike
    # the three caps above, nothing else bounds how many `PolicyException` rows one Rule
    # can accumulate. Requires an already-privileged actor (holding the rule's own
    # approver_role) to create volume, so lower risk than the three above, but the same
    # "config-driven ceiling, not an unbounded resource" principle applies.
    max_active_exceptions_per_rule: int = 50

    # SEC-003: upload validation limits (see app/contracts/infrastructure/document_scanner.py
    # for the full malware/type-spoofing scope decision).
    document_max_size_bytes: int = 25_000_000  # 25 MB

    # BR-APR-003's SLA duration is an explicit `TBD` pending customer discovery
    # (docs/03-domain/approvals.md "SLA and escalation") -- a flat 48h (2 "business
    # days", treated as flat wall-clock time rather than real business-day calendar
    # arithmetic, which is out of scope this round) is the documented hackathon default.
    approval_request_sla_hours: int = 48
    # How often the SLA-expiry sweep runs (cadence is a documented TBD like the SLA itself).
    approval_expiry_sweep_interval_seconds: int = 900

    # A Decision's `valid_until` duration is likewise a documented `TBD` (BR-DEC-004
    # doesn't pin a number) -- 90 days is a plain, defensible default pending real data.
    decision_valid_days: int = 90

    # BR-DEC-004 / FEATURE-6.4: cadence of the platform-wide sweep that flags stale
    # Decisions for re-evaluation. Hourly is a placeholder, not a commercial decision --
    # TBD alongside the Decision validity window above; see
    # app/approvals/application/reevaluation_service.py for the staleness-window tradeoff.
    decision_reevaluation_interval_seconds: int = 3600
    # Security review (2026-10-03): the sweep is platform-wide and each stale Decision costs a
    # full ComplianceReview, so one tenant's many live Decisions could otherwise monopolise a
    # run. Capping candidates per run (oldest first, so the backlog still drains) bounds the
    # worst-case run length regardless of any single tenant's volume.
    decision_reevaluation_batch_size: int = 100
    # FEATURE-6.5 (BR-DEC-004): how many re-evaluation reviews a single flagged Decision may
    # run in total, counting its first one. Once the latest one's approval chain has expired
    # and this many have been spent, the Decision stops retrying and
    # `compliance.reevaluation_failed` is emitted once as the operator alert.
    decision_reevaluation_max_attempts: int = Field(default=3, ge=1)

    # FEATURE-8.1/ADR-007 spike (2026-10-07): the AnchoringProvider's active implementation is
    # an explicit, named choice -- never sniffed from whether credentials happen to be set --
    # same "config-only swap" shape as ai_extraction_primary_model's provider choice. Must be
    # exactly one of AnchoringProvider.provider_name's two real values -- "transparency_log" or
    # "constellation_digital_evidence" -- the same strings anchoring_service.get_provider_by_name
    # matches against and BlockchainAnchor.provider stores, so there is only ever one naming
    # scheme for a provider in this codebase. (Security review, 2026-10-07: an earlier version
    # of this comment said the short form "constellation" activates it -- that string matches
    # neither constant and would have made every new submission fail closed with "Unknown
    # anchoring provider" the day this setting was actually changed.)
    # "transparency_log" needs no external credentials and is the honest default until a real
    # Constellation Digital Evidence Depository (DED) API key is provisioned (not self-service --
    # see docs/06-blockchain/anchoring-providers.md's spike findings); "constellation_digital_
    # evidence" activates the real adapter once constellation_ded_* below are all set.
    anchoring_provider: str = "transparency_log"

    # Constellation DED (docs/06-blockchain/anchoring-providers.md): org_id/tenant_id/api_key are
    # issued directly by Constellation, not self-service -- see the spike findings. private_key is
    # a 64-hex-char SECP256K1 signing key (never the JWT/storage secret), generated once and kept
    # outside version control; None until provisioned.
    # Security review (2026-10-07): signing (constellation_provider.py, via the official SDK)
    # goes through the `ecdsa` pure-Python package, which has a documented history of
    # timing-side-channel concerns for SECP256k1. Inert today (this setting is None), but
    # whoever provisions this key (Plane #198) should re-check that package's crypto backend
    # first.
    constellation_ded_base_url: str = "https://de-api.constellationnetwork.io/v1"
    constellation_ded_api_key: str | None = None
    constellation_ded_org_id: str | None = None
    constellation_ded_tenant_id: str | None = None
    constellation_ded_private_key: str | None = None
    constellation_ded_timeout_seconds: float = 15.0

    # Transparency-log fallback (docs/09-planning/risks.md risk 4): a local git repository that
    # a real deployment pushes to a public remote (not done by this backend itself -- see that
    # module's own docstring) so the log is genuinely third-party-checkable, not just locally
    # inspectable. signing_key_path is deliberately NOT inside repo_path: repo_path's contents are
    # meant to be published; the private key must never be.
    transparency_log_repo_path: str = "./data/transparency-log"
    transparency_log_signing_key_path: str = "./data/transparency-log-signing-key"

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
        if (
            self.environment == "production"
            and self.integration_credentials_encryption_key == _DEV_INTEGRATION_CREDENTIALS_KEY
        ):
            raise ValueError(
                "INTEGRATION_CREDENTIALS_ENCRYPTION_KEY must be set in production with a "
                "real Fernet key (generate with: python -c \"from cryptography.fernet import "
                'Fernet; print(Fernet.generate_key().decode())"), never the committed dev key'
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
        if self.environment == "production" and not self.openrouter_api_key:
            # #116: without this, the first contract upload in production fails with an
            # opaque 401 from OpenRouter deep inside extraction_service -- not at startup,
            # and not with any indication of which setting is the actual cause.
            raise ValueError(
                "OPENROUTER_API_KEY must be set in production -- without it, every "
                "contract extraction call fails at first use instead of at startup"
            )
        return self

    @model_validator(mode="after")
    def _require_active_anchoring_provider_credentials(self) -> "Settings":
        """#116: `ANCHORING_PROVIDER` is a plain config switch (`anchoring-providers.md`),
        not itself production-gated -- a developer can legitimately flip it to
        `constellation_digital_evidence` in any environment to test against the real
        Constellation DED API. But doing so with any of the four `CONSTELLATION_DED_*`
        settings still unset used to fail deep inside `ConstellationAnchoringProvider.
        submit_hash` (a signing error or a 401), the first time a Decision was actually
        anchored -- not at startup, and not naming which setting was missing. Checked
        regardless of `environment`, unlike the production-only secrets above: choosing
        this provider is itself the signal that these are now required, not the
        environment."""
        if self.anchoring_provider == "constellation_digital_evidence":
            missing = [
                env_name
                for env_name, value in (
                    ("CONSTELLATION_DED_API_KEY", self.constellation_ded_api_key),
                    ("CONSTELLATION_DED_ORG_ID", self.constellation_ded_org_id),
                    ("CONSTELLATION_DED_TENANT_ID", self.constellation_ded_tenant_id),
                    ("CONSTELLATION_DED_PRIVATE_KEY", self.constellation_ded_private_key),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "ANCHORING_PROVIDER=constellation_digital_evidence requires these "
                    f"environment variables, which are not set: {', '.join(missing)}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
