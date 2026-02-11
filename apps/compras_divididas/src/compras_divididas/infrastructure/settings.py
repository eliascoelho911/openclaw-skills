"""Typed settings for compras-divididas infrastructure."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")
    openai_timeout_seconds: int = Field(default=30, validation_alias="OPENAI_TIMEOUT")
    prompt_version: str = Field(default="v1", validation_alias="PROMPT_VERSION")
    schema_version: str = Field(default="v1", validation_alias="SCHEMA_VERSION")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()  # type: ignore[call-arg]
