"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for API and persistence layers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/compras_divididas",
        alias="DATABASE_URL",
    )
    app_timezone: str = Field(default="America/Sao_Paulo", alias="APP_TIMEZONE")
    mcp_api_base_url: str = Field(
        default="http://127.0.0.1:8000",
        alias="MCP_API_BASE_URL",
    )
    mcp_api_timeout_seconds: float = Field(
        default=10.0,
        alias="MCP_API_TIMEOUT_SECONDS",
        gt=0,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance for the current process."""

    return Settings()
