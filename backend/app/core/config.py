from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-with-32-bytes-min"  # noqa: S105 — apenas desenvolvimento


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
