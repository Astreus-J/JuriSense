from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
