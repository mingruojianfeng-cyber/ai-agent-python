from app.core.config import Settings, mask_secret


def test_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "demo-agent")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-secret")
    monkeypatch.setenv("LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("SEARCH_API_KEY", "search-test-key")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("CHAT_MEMORY_TYPE", "database")
    monkeypatch.setenv("CHAT_MEMORY_MAX_MESSAGES", "8")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/yu_ai_agent")

    settings = Settings()

    assert settings.app_name == "demo-agent"
    assert settings.app_env == "test"
    assert settings.llm_provider == "deepseek"
    assert settings.llm_base_url == "https://api.example.com/v1"
    assert settings.llm_api_key == "sk-test-secret"
    assert settings.llm_model == "qwen-plus"
    assert settings.search_api_key == "search-test-key"
    assert settings.request_timeout_seconds == 30
    assert settings.chat_memory_type == "database"
    assert settings.chat_memory_max_messages == 8
    assert settings.database_url == "postgresql+asyncpg://user:password@localhost:5432/yu_ai_agent"


def test_mask_secret_hides_sensitive_value() -> None:
    assert mask_secret("") == ""
    assert mask_secret("short") == "*****"
    assert mask_secret("sk-test-secret") == "sk-t******cret"
