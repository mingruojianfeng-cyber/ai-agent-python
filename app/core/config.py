from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def mask_secret(value: str) -> str:
    """Mask secrets before logging, similar to hiding API keys in Java log output."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    For Java developers: this plays the role of `application.yml` plus
    `@ConfigurationProperties` or `@Value`. Service code reads one typed object
    instead of reaching into environment variables directly.
    """

    app_name: str = "yu-ai-agent-python"
    app_env: str = "local"
    llm_provider: str = "openai-compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    llm_reasoning_effort: str = ""
    llm_extra_body_json: str = ""
    request_timeout_seconds: int = Field(default=60, ge=1)
    chat_memory_type: str = "memory"
    chat_memory_max_messages: int = Field(default=20, ge=1)
    database_url: str = "sqlite+aiosqlite:///./chat_memory.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def masked_llm_api_key(self) -> str:
        """Return a log-safe API key, like a Java DTO field prepared for logging."""
        return mask_secret(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a singleton-like Settings instance.

    For Java developers: this is close to letting Spring manage one config bean
    and injecting that same bean wherever it is needed.
    """
    return Settings()
