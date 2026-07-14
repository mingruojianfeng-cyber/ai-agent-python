# lru_cache 用于将无参配置工厂缓存成进程内单例。
from functools import lru_cache

# Field 为 DTO/配置字段附加默认值和校验规则。
from pydantic import Field

# BaseSettings 负责从环境变量读取配置；SettingsConfigDict 配置其读取行为。
from pydantic_settings import BaseSettings, SettingsConfigDict


def mask_secret(value: str) -> str:
    """在日志输出前脱敏密钥，避免泄露 API Key。"""
    # 该函数只负责日志展示层脱敏，返回值不能当成真正密钥继续使用。
    # 空字符串没有可保留的前后缀，直接返回空展示值。
    if not value:
        return ""
    # 短密钥若保留前后四位会完整泄露，因此全部替换成星号。
    if len(value) <= 8:
        return "*" * len(value)
    # 切片保留首尾四位，中间按原长度填充星号，便于排查配置又不暴露密钥。
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class Settings(BaseSettings):
    """从环境变量加载应用配置，作用类似 Java 的配置属性对象。"""

    # 每个类属性都是一个配置项；环境变量 APP_NAME 会覆盖 app_name 的默认值。
    app_name: str = "yu-ai-agent-python"
    app_env: str = "local"
    llm_provider: str = "openai-compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    llm_reasoning_effort: str = ""
    llm_extra_body_json: str = ""
    search_api_key: str = ""
    # ge=1 相当于 Java Bean Validation 的 @Min(1)。
    request_timeout_seconds: int = Field(default=60, ge=1)
    chat_memory_type: str = "memory"
    chat_memory_max_messages: int = Field(default=20, ge=1)
    database_url: str = "sqlite+aiosqlite:///./chat_memory.db"

    # 必须与 pgvector 表的 vector(N) 维度一致。
    embedding_dimensions: int = Field(default=1536, ge=1, le=8192)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    # rag是否开启，保证现有聊天流程是否开启
    rag_enabled: bool = False
    # 配置embedding模型
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    # 命中片段低于该相似度时，不允许作为知识库依据回答。
    rag_min_score: float = Field(default=0.45, ge=0, le=1)

    # Pydantic Settings 负责环境变量绑定、类型转换和校验。
    # Java 对照：相当于 Spring Boot 的 @ConfigurationProperties。

    # 指定 .env 文件、编码和对未知环境变量的兼容策略。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # @property 让调用方以属性而不是方法形式读取脱敏密钥。
    @property
    def masked_llm_api_key(self) -> str:
        """返回可安全写入日志的脱敏模型密钥。"""
        return mask_secret(self.llm_api_key)


# 首次调用创建 Settings，后续调用复用同一对象，近似 Spring 的 singleton Bean。
@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的配置实例。"""
    # 函数缓存实现进程内复用，类似单例 Bean，但不会跨进程共享对象。
    return Settings()
