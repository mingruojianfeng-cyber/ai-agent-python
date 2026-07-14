from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.rag.embedding_client import EmbeddingClient, EmbeddingClientError


class FakeEmbeddings:
    def __init__(self) -> None:
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs

        return SimpleNamespace(
            data = [
                SimpleNamespace(index=1, embedding=[0.3, 0.4]),
                SimpleNamespace(index=0, embedding=[0.1, 0.2]),
            ]
        )

class FakeEmbeddingClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.embeddings = FakeEmbeddings()

@pytest.mark.asyncio
async def test_embedding_client_returns_vectors_in_input_order() -> None:
    created_clients: list[FakeEmbeddingClient] = []

    def client_factory(**kwargs) -> FakeEmbeddingClient:
        client = FakeEmbeddingClient(**kwargs)
        created_clients.append(client)
        return client

    settings = Settings(
        embedding_base_url="https://embedding.example/v1",
        embedding_api_key="embedding-secret",
        embedding_model="text-embedding-test",
        embedding_dimensions=2,
    )
    client = EmbeddingClient(settings=settings, client_factory=client_factory)

    vectors = await client.embed(["第一段文本", "第二段文本"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert created_clients[0].kwargs == {
        "api_key": "embedding-secret",
        "base_url": "https://embedding.example/v1",
        "timeout": 60,
    }
    assert created_clients[0].embeddings.kwargs == {
        "model": "text-embedding-test",
        "input": ["第一段文本", "第二段文本"],
    }


@pytest.mark.asyncio
async def test_embedding_client_returns_empty_list_without_calling_provider() -> None:
    settings = Settings(
        embedding_base_url="https://embedding.example/v1",
        embedding_api_key="embedding-secret",
        embedding_model="text-embedding-test",
        embedding_dimensions=2,
    )
    client = EmbeddingClient(settings=settings, client_factory=FakeEmbeddingClient)

    assert await client.embed([]) == []


@pytest.mark.asyncio
async def test_embedding_client_rejects_vector_with_wrong_dimensions() -> None:
    class WrongDimensionEmbeddings:
        async def create(self, **kwargs):
            return SimpleNamespace(
                data=[SimpleNamespace(index=0, embedding=[0.1, 0.2, 0.3])]
            )

    class WrongDimensionClient:
        def __init__(self, **kwargs) -> None:
            self.embeddings = WrongDimensionEmbeddings()

    settings = Settings(
        embedding_base_url="https://embedding.example/v1",
        embedding_api_key="embedding-secret",
        embedding_model="text-embedding-test",
        embedding_dimensions=2,
    )
    client = EmbeddingClient(settings=settings, client_factory=WrongDimensionClient)

    with pytest.raises(EmbeddingClientError, match="dimension"):
        await client.embed(["一段文本"])
