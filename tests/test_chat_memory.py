import pytest

from app.memory.chat_memory import DatabaseChatMemory, InMemoryChatMemory


@pytest.mark.asyncio
async def test_in_memory_chat_memory_keeps_messages_isolated_by_chat_id() -> None:
    memory = InMemoryChatMemory()

    await memory.add_message("chat-a", "user", "你好")
    await memory.add_message("chat-b", "user", "另一段会话")

    assert await memory.get_messages("chat-a", limit=10) == [
        {"role": "user", "content": "你好"},
    ]
    assert await memory.get_messages("chat-b", limit=10) == [
        {"role": "user", "content": "另一段会话"},
    ]


@pytest.mark.asyncio
async def test_in_memory_chat_memory_trims_old_messages() -> None:
    memory = InMemoryChatMemory()

    await memory.add_message("chat-a", "user", "第一条")
    await memory.add_message("chat-a", "assistant", "第二条")
    await memory.add_message("chat-a", "user", "第三条")
    await memory.trim_messages("chat-a", max_messages=2)

    assert await memory.get_messages("chat-a", limit=10) == [
        {"role": "assistant", "content": "第二条"},
        {"role": "user", "content": "第三条"},
    ]


@pytest.mark.asyncio
async def test_database_chat_memory_persists_and_trims_messages_with_sqlite(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'chat_memory.db'}"
    memory = DatabaseChatMemory(database_url=database_url)
    await memory.init_schema()

    await memory.add_message("chat-a", "user", "第一条")
    await memory.add_message("chat-a", "assistant", "第二条")
    await memory.add_message("chat-a", "user", "第三条")
    await memory.add_message("chat-b", "user", "另一段会话")
    await memory.trim_messages("chat-a", max_messages=2)

    reloaded_memory = DatabaseChatMemory(database_url=database_url)

    assert await reloaded_memory.get_messages("chat-a", limit=10) == [
        {"role": "assistant", "content": "第二条"},
        {"role": "user", "content": "第三条"},
    ]
    assert await reloaded_memory.get_messages("chat-b", limit=10) == [
        {"role": "user", "content": "另一段会话"},
    ]

    await memory.close()
    await reloaded_memory.close()


@pytest.mark.asyncio
async def test_database_chat_memory_accepts_postgresql_url() -> None:
    memory = DatabaseChatMemory(
        database_url="postgresql+asyncpg://user:password@localhost:5432/yu_ai_agent"
    )

    assert memory.engine.url.drivername == "postgresql+asyncpg"
    await memory.close()
