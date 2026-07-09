from collections import defaultdict
from typing import Protocol

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


ChatMessage = dict[str, str]

metadata = MetaData()

chat_messages = Table(
    "chat_messages",
    metadata,
    # Java 开发者理解：这里等价于 JPA 实体里的 @Id，SQLite 会自动适配自增整数。
    # PostgreSQL 上 SQLAlchemy 会生成 BIGSERIAL / identity 风格的自增列。
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chat_id", String(128), nullable=False, index=True),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


class ChatMemory(Protocol):
    """会话记忆接口，作用类似 Java 里的 ChatMemory。"""

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        """按会话 ID 获取最近的历史消息。"""

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        """保存一条消息。"""

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        """裁剪窗口，只保留最近 max_messages 条消息。"""


class InMemoryChatMemory:
    """基于内存的会话记忆，类似 Java 的 InMemoryChatMemoryRepository。"""

    def __init__(self) -> None:
        self._messages_by_chat_id: dict[str, list[ChatMessage]] = defaultdict(list)

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        messages = self._messages_by_chat_id[chat_id]
        return [message.copy() for message in messages[-limit:]]

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        self._messages_by_chat_id[chat_id].append({"role": role, "content": content})

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        messages = self._messages_by_chat_id[chat_id]
        if len(messages) > max_messages:
            self._messages_by_chat_id[chat_id] = messages[-max_messages:]


class DatabaseChatMemory:
    """基于 SQLAlchemy 的数据库会话记忆，支持 SQLite 和 PostgreSQL。"""

    def __init__(self, database_url: str, engine: AsyncEngine | None = None) -> None:
        self.engine = engine or create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._schema_initialized = False

    async def init_schema(self) -> None:
        """初始化表结构，类似 Spring Boot 启动时执行 schema 初始化。"""
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
        self._schema_initialized = True

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        await self._ensure_schema()
        latest_ids_query = (
            select(chat_messages.c.id)
            .where(chat_messages.c.chat_id == chat_id)
            .order_by(chat_messages.c.id.desc())
            .limit(limit)
            .subquery()
        )
        query = (
            select(chat_messages.c.role, chat_messages.c.content)
            .where(chat_messages.c.id.in_(select(latest_ids_query.c.id)))
            .order_by(chat_messages.c.id.asc())
        )
        async with self.session_factory() as session:
            rows = (await session.execute(query)).all()
        return [{"role": row.role, "content": row.content} for row in rows]

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        await self._ensure_schema()
        query = insert(chat_messages).values(chat_id=chat_id, role=role, content=content)
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(query)

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        await self._ensure_schema()
        latest_ids_query = (
            select(chat_messages.c.id)
            .where(chat_messages.c.chat_id == chat_id)
            .order_by(chat_messages.c.id.desc())
            .limit(max_messages)
            .subquery()
        )
        query = delete(chat_messages).where(
            chat_messages.c.chat_id == chat_id,
            chat_messages.c.id.not_in(select(latest_ids_query.c.id)),
        )
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(query)

    async def close(self) -> None:
        """释放连接池资源，类似关闭 DataSource。"""
        await self.engine.dispose()

    async def _ensure_schema(self) -> None:
        if not self._schema_initialized:
            await self.init_schema()
