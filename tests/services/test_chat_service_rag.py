import pytest

from app.memory.chat_memory import InMemoryChatMemory
from app.rag.schemas import RetrievedChunk
from app.services.chat_service import ChatService, RAG_NO_ANSWER


class FakeLLMClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] | None = None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "基于知识库的回答"


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks

    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        return self.chunks


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        knowledge_base_id="knowledge-base-1",
        document_id="document-1",
        document_name="rag-intro.md",
        chunk_index=0,
        content="RAG 是检索增强生成。",
        score=0.8,
    )


@pytest.mark.asyncio
async def test_rag_chat_uses_knowledge_base_scoped_memory() -> None:
    memory = InMemoryChatMemory()
    await memory.add_message("chat-1", "assistant", RAG_NO_ANSWER)
    llm_client = FakeLLMClient()
    service = ChatService(llm_client=llm_client, chat_memory=memory)

    result = await service.chat_with_rag(
        message="什么是 RAG？",
        chat_id="chat-1",
        knowledge_base_id="knowledge-base-1",
        retriever=FakeRetriever([_chunk()]),
    )

    assert result.answer == "基于知识库的回答"
    assert llm_client.messages is not None
    assert {message["content"] for message in llm_client.messages}.isdisjoint({RAG_NO_ANSWER})
    assert await memory.get_messages("chat-1", limit=10) == [
        {"role": "assistant", "content": RAG_NO_ANSWER}
    ]
    assert await memory.get_messages("chat-1:kb:knowledge-base-1", limit=10) == [
        {"role": "user", "content": "什么是 RAG？"},
        {"role": "assistant", "content": "基于知识库的回答"},
    ]


@pytest.mark.asyncio
async def test_rag_chat_does_not_persist_retrieval_refusal() -> None:
    memory = InMemoryChatMemory()
    service = ChatService(llm_client=FakeLLMClient(), chat_memory=memory)

    result = await service.chat_with_rag(
        message="没有匹配资料的问题",
        chat_id="chat-1",
        knowledge_base_id="knowledge-base-1",
        retriever=FakeRetriever([]),
    )

    assert result.answer == RAG_NO_ANSWER
    assert await memory.get_messages("chat-1:kb:knowledge-base-1", limit=10) == []
