from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def mask_secret(value: str) -> str:
    """在日志输出前脱敏密钥，避免泄露 API Key。"""
    # 该函数只负责日志展示层脱敏，返回值不能当成真正密钥继续使用。
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class Settings(BaseSettings):
    """从环境变量加载应用配置，作用类似 Java 的配置属性对象。"""

    app_name: str = "yu-ai-agent-python"
    app_env: str = "local"
    llm_provider: str = "openai-compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    llm_reasoning_effort: str = ""
    llm_extra_body_json: str = ""
    search_api_key: str = ""
    request_timeout_seconds: int = Field(default=60, ge=1)
    chat_memory_type: str = "memory"
    chat_memory_max_messages: int = Field(default=20, ge=1)
    database_url: str = "sqlite+aiosqlite:///./chat_memory.db"

    # Pydantic Settings 负责环境变量绑定、类型转换和校验。
    # Java 对照：相当于 Spring Boot 的 @ConfigurationProperties。

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def masked_llm_api_key(self) -> str:
        """返回可安全写入日志的脱敏模型密钥。"""
        return mask_secret(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的配置实例。"""
    # 函数缓存实现进程内复用，类似单例 Bean，但不会跨进程共享对象。
    return Settings()
