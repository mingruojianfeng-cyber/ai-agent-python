import pytest
from pydantic import ValidationError

from app.rag.schemas import DocumentStatus, RetrievedChunk


def test_document_status_uses_stable_string_values() -> None:
    assert DocumentStatus.PENDING == "PENDING"
    assert DocumentStatus.READY == "READY"
    assert DocumentStatus.FAILED == "FAILED"


def test_retrieved_chunk_is_immutable() -> None:
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        knowledge_base_id="kb-1",
        document_id="doc-1",
        document_name="rag-guide.md",
        chunk_index=0,
        content="RAG 会先检索相关文档，再生成回答。",
        score=0.92,
    )

    with pytest.raises(ValidationError):
        chunk.score = 0.1