from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class Settings(BaseSettings):
    app_name: str = "yu-ai-agent-python"
    app_env: str = "local"
    llm_provider: str = "openai-compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    llm_reasoning_effort: str = ""
    llm_extra_body_json: str = ""
    request_timeout_seconds: int = Field(default=60, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def masked_llm_api_key(self) -> str:
        return mask_secret(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
