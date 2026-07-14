import logging

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.rag.retriever import RetrievalError, VectorRetriever
from app.rag.schemas import RetrievedChunk


class FakeEmbeddingClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2]]


class FakeVectorStore:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []

    async def search_vector(
        self,
        knowledge_base_id: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[RetrievedChunk]:
        return self.chunks


class FailingVectorStore:
    async def search_vector(
        self,
        knowledge_base_id: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[RetrievedChunk]:
        raise SQLAlchemyError("database unavailable")


def _chunk(score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        knowledge_base_id="knowledge-base-1",
        document_id="document-1",
        document_name="rag-intro.md",
        chunk_index=0,
        content="RAG 是检索增强生成。",
        score=score,
    )


@pytest.mark.asyncio
async def test_retriever_wraps_vector_store_database_error() -> None:
    retriever = VectorRetriever(
        embedding_client=FakeEmbeddingClient(),
        vector_store=FailingVectorStore(),
        min_score=0.1,
    )

    with pytest.raises(RetrievalError, match="vector search"):
        await retriever.retrieve("什么是 RAG？", "knowledge-base-1", top_k=5)


@pytest.mark.asyncio
async def test_retriever_logs_retrieval_scores(caplog: pytest.LogCaptureFixture) -> None:
    retriever = VectorRetriever(
        embedding_client=FakeEmbeddingClient(),
        vector_store=FakeVectorStore([_chunk(0.8), _chunk(0.05)]),
        min_score=0.1,
    )
    caplog.set_level(logging.INFO, logger="yu_ai_agent.rag")

    chunks = await retriever.retrieve("什么是 RAG？", "knowledge-base-1", top_k=5)

    assert chunks == [_chunk(0.8)]
    assert "rag_retrieval knowledge_base_id=knowledge-base-1 retrieved=2 accepted=1" in caplog.text
