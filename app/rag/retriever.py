from typing import Protocol

from app.rag.embedding_client import EmbeddingClient, EmbeddingClientError
from app.rag.schemas import RetrievedChunk
from app.rag.vector_store import PgVectorStore


class RetrievalError(Exception):
    """RAG 检索失败。"""


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int,
    ) -> list[RetrievedChunk]: ...


class VectorRetriever:
    """纯向量检索器：查询向量化 → pgvector Top-K → 相似度过滤。"""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_store: PgVectorStore,
        min_score: float,
    ) -> None:
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.min_score = min_score

    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        try:
            vectors = await self.embedding_client.embed([query])
        except EmbeddingClientError as exc:
            raise RetrievalError("Failed to embed retrieval query.") from exc

        if len(vectors) != 1:
            raise RetrievalError("Embedding provider returned unexpected query vectors.")

        chunks = await self.vector_store.search_vector(
            knowledge_base_id=knowledge_base_id,
            query_embedding=vectors[0],
            limit=top_k,
        )

        return [
            chunk
            for chunk in chunks
            if chunk.score >= self.min_score
        ]