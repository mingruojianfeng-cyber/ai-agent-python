import pytest

from app.memory.chat_memory import DatabaseChatMemory, InMemoryChatMemory
from app.services.chat_service import ChatService, SYSTEM_PROMPT


class FakeLLMClient:
    def __init__(self) -> None:
        self.messages = None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "模型回答"

    async def stream_chat(self, messages: list[dict[str, str]]):
        self.messages = messages
        for chunk in ["模型", "回答"]:
            yield chunk


@pytest.mark.asyncio
async def test_chat_service_sends_history_and_saves_current_turn() -> None:
    memory = InMemoryChatMemory()
    await memory.add_message("chat-a", "user", "上一轮用户问题")
    await memory.add_message("chat-a", "assistant", "上一轮模型回答")
    llm_client = FakeLLMClient()
    service = ChatService(llm_client=llm_client, chat_memory=memory, max_messages=4)

    answer = await service.chat("这一轮问题", "chat-a")

    assert answer == "模型回答"
    assert llm_client.messages == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "上一轮用户问题"},
        {"role": "assistant", "content": "上一轮模型回答"},
        {"role": "user", "content": "这一轮问题"},
    ]
    assert await memory.get_messages("chat-a", limit=10) == [
        {"role": "user", "content": "上一轮用户问题"},
        {"role": "assistant", "content": "上一轮模型回答"},
        {"role": "user", "content": "这一轮问题"},
        {"role": "assistant", "content": "模型回答"},
    ]


@pytest.mark.asyncio
async def test_chat_service_trims_memory_after_saving_answer() -> None:
    memory = InMemoryChatMemory()
    service = ChatService(llm_client=FakeLLMClient(), chat_memory=memory, max_messages=2)

    await service.chat("第一轮问题", "chat-a")
    await service.chat("第二轮问题", "chat-a")

    assert await memory.get_messages("chat-a", limit=10) == [
        {"role": "user", "content": "第二轮问题"},
        {"role": "assistant", "content": "模型回答"},
    ]


@pytest.mark.asyncio
async def test_chat_service_streams_answer_and_saves_complete_turn() -> None:
    memory = InMemoryChatMemory()
    llm_client = FakeLLMClient()
    service = ChatService(llm_client=llm_client, chat_memory=memory, max_messages=4)

    chunks = [chunk async for chunk in service.stream_chat("这一轮问题", "chat-a")]

    assert chunks == ["模型", "回答"]
    assert llm_client.messages == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "这一轮问题"},
    ]
    assert await memory.get_messages("chat-a", limit=10) == [
        {"role": "user", "content": "这一轮问题"},
        {"role": "assistant", "content": "模型回答"},
    ]


@pytest.mark.asyncio
async def test_chat_service_can_create_postgresql_database_memory() -> None:
    memory = ChatService._create_chat_memory(
        memory_type="database",
        database_url="postgresql+asyncpg://user:password@localhost:5432/yu_ai_agent",
    )

    assert isinstance(memory, DatabaseChatMemory)
    assert memory.engine.url.drivername == "postgresql+asyncpg"
    await memory.close()
