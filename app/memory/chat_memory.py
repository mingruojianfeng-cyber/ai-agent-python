# defaultdict 允许按会话 ID 懒创建消息列表。
from collections import defaultdict
# Protocol 声明“鸭子类型”接口，实现类不必显式继承它。
from typing import Protocol

# SQLAlchemy Core 用表对象和查询表达式代替手写 SQL，下面导入建表、查询、插入和删除能力。
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, delete, func, insert, select
# 异步引擎与会话工厂使数据库 I/O 可 await，不阻塞 FastAPI 事件循环。
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


# 聊天消息统一采用 OpenAI-compatible 的 {role, content} 字典形状。
ChatMessage = dict[str, str]

# 类型别名只描述数据形状；它不像 Java class 一样自带构造器和运行时行为。

# MetaData 汇总本模块表定义，create_all 会据此生成数据库表结构。
metadata = MetaData()

# 使用 SQLAlchemy Core Table 描述表；这里没有创建传统 ORM Entity 类。
chat_messages = Table(
    "chat_messages",
    metadata,
    # Java 开发者理解：这里等价于 JPA 实体里的 @Id，SQLite 会自动适配自增整数。
    # PostgreSQL 上 SQLAlchemy 会生成 BIGSERIAL / identity 风格的自增列。
    Column("id", Integer, primary_key=True, autoincrement=True),
    # chat_id 建索引，优化“按会话读取最近消息”的最常见查询。
    Column("chat_id", String(128), nullable=False, index=True),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    # server_default 在数据库端生成时间，避免应用服务器时钟直接参与写入。
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
        # defaultdict 在首次访问不存在的 chat_id 时自动创建空列表，类似 Map.computeIfAbsent。
        self._messages_by_chat_id: dict[str, list[ChatMessage]] = defaultdict(list)

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        # 取出当前会话列表；defaultdict 会在首次访问时生成空列表。
        messages = self._messages_by_chat_id[chat_id]
        # 切片取最后 limit 条，再 copy 防止调用方修改内部记忆中的原字典。
        return [message.copy() for message in messages[-limit:]]

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        # 以与模型 API 相同的 role/content 结构保存，后续可直接拼进 messages。
        self._messages_by_chat_id[chat_id].append({"role": role, "content": content})

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        messages = self._messages_by_chat_id[chat_id]
        # 仅在超出窗口时重新切片，正常情况下避免无意义的新列表分配。
        if len(messages) > max_messages:
            self._messages_by_chat_id[chat_id] = messages[-max_messages:]


class DatabaseChatMemory:
    """基于 SQLAlchemy 的数据库会话记忆，支持 SQLite 和 PostgreSQL。"""

    def __init__(self, database_url: str, engine: AsyncEngine | None = None) -> None:
        # engine 可从外部注入，便于测试复用内存数据库；未注入时才根据 URL 创建引擎。
        # 传入 engine 时方便测试控制连接；否则根据配置 URL 创建真实异步引擎。
        self.engine = engine or create_async_engine(database_url)
        # 提交后不使对象过期，避免读取结果时额外触发数据库刷新。
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._schema_initialized = False

    async def init_schema(self) -> None:
        """初始化表结构，类似 Spring Boot 启动时执行 schema 初始化。"""
        # begin() 提供连接和事务边界，退出上下文时自动提交或回滚。
        async with self.engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
        self._schema_initialized = True

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        await self._ensure_schema()
        # 子查询先选出最新 N 条 id，外层再按正序取回，保证展示仍是时间正序。
        latest_ids_query = (
            select(chat_messages.c.id)
            .where(chat_messages.c.chat_id == chat_id)
            .order_by(chat_messages.c.id.desc())
            .limit(limit)
            .subquery()
        )
        # 外层查询只读取模型需要的 role/content 字段，不额外读取 id、创建时间。
        query = (
            select(chat_messages.c.role, chat_messages.c.content)
            .where(chat_messages.c.id.in_(select(latest_ids_query.c.id)))
            .order_by(chat_messages.c.id.asc())
        )
        # session.begin() 负责事务提交与异常回滚，类似 Java 的 @Transactional 边界。
        async with self.session_factory() as session:
            rows = (await session.execute(query)).all()
        # Row 属性映射回统一的 ChatMessage 字典，隔离 SQLAlchemy 结果对象。
        return [{"role": row.role, "content": row.content} for row in rows]

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        await self._ensure_schema()
        # 构造参数化 INSERT 表达式，SQLAlchemy 负责绑定参数以避免手写拼接 SQL。
        query = insert(chat_messages).values(chat_id=chat_id, role=role, content=content)
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(query)

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        await self._ensure_schema()
        # 删除时复用“最新 N 条 id”子查询，用 NOT IN 删除更早的记录。
        latest_ids_query = (
            select(chat_messages.c.id)
            .where(chat_messages.c.chat_id == chat_id)
            .order_by(chat_messages.c.id.desc())
            .limit(max_messages)
            .subquery()
        )
        # where 的多个条件以 AND 连接，只影响当前 chat_id 的过期消息。
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
        # 延迟建表让构造对象无 I/O；首次实际读写时再初始化 schema。
        if not self._schema_initialized:
            await self.init_schema()
