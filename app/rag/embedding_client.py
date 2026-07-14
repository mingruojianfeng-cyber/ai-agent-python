from collections.abc import Callable
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings, get_settings


class EmbeddingClientError(Exception):
    """Embedding 调用或返回结果不合法时抛出的项目异常。"""


class OpenAICompatibleEmbeddingClientProtocol(Protocol):
    """Embedding SDK 所需的最小接口。"""

    embeddings: Any


class EmbeddingClient:
    """独立的 OpenAI-compatible Embedding 客户端。"""

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., OpenAICompatibleEmbeddingClientProtocol] = AsyncOpenAI,
    ) -> None:
        self.settings = settings or get_settings()
        if not self.settings.embedding_base_url:
            raise ValueError("EMBEDDING_BASE_URL must be configured.")
        if not self.settings.embedding_api_key:
            raise ValueError("EMBEDDING_API_KEY must be configured.")
        if not self.settings.embedding_model:
            raise ValueError("EMBEDDING_MODEL must be configured.")

        self.model = self.settings.embedding_model
        self.embedding_dimensions = self.settings.embedding_dimensions
        self._client = client_factory(
            api_key=self.settings.embedding_api_key,
            base_url=self.settings.embedding_base_url,
            timeout=self.settings.request_timeout_seconds,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为与输入顺序一致的向量列表。"""

        if not texts:
            return []

        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=texts,
            )
        except OpenAIError as exc:  # noqa: F821
            raise EmbeddingClientError("Embedding provider request failed.") from exc

        vectors_by_index: list[list[float] | None] = [None] * len(texts)

        for item in response.data:
            if item.index < 0 or item.index >= len(texts):
                raise EmbeddingClientError("Embedding provider returned invalid index.")

            vector = list(item.embedding)
            if len(vector) != self.embedding_dimensions:
                raise EmbeddingClientError(
                    "Embedding provider returned vector with unexpected dimension."
                )

            vectors_by_index[item.index] = vector

        if any(vector is None for vector in vectors_by_index):
            raise EmbeddingClientError("Embedding provider returned incomplete vectors.")

        return [vector for vector in vectors_by_index if vector is not None]