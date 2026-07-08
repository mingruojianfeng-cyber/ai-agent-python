from app.core.config import Settings, mask_secret


def test_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "demo-agent")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-secret")
    monkeypatch.setenv("LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "30")

    settings = Settings()

    assert settings.app_name == "demo-agent"
    assert settings.app_env == "test"
    assert settings.llm_base_url == "https://api.example.com/v1"
    assert settings.llm_api_key == "sk-test-secret"
    assert settings.llm_model == "qwen-plus"
    assert settings.request_timeout_seconds == 30


def test_mask_secret_hides_sensitive_value() -> None:
    assert mask_secret("") == ""
    assert mask_secret("short") == "*****"
    assert mask_secret("sk-test-secret") == "sk-t******cret"
