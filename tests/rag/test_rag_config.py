
from app.core.config import Settings


def test_setting_reads_rag(monkeypatch) -> None:
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://embedding.example/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-secret")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-test")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "8")
    monkeypatch.setenv("RAG_TOP_K", "8")

    settings = Settings()

    assert settings.rag_enabled is True
    assert settings.embedding_base_url == "https://embedding.example/v1"
    assert settings.embedding_api_key == "embedding-secret"
    assert settings.embedding_model == "text-embedding-test"
    assert settings.embedding_dimensions == 8
    assert settings.rag_top_k == 8
