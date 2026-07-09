import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Protocol


ChatMessage = dict[str, str]


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
    """基于 SQLite 的会话记忆，后续可替换为 MySQL/PostgreSQL 实现。"""

    def __init__(self, database_url: str) -> None:
        self.database_path = self._parse_sqlite_url(database_url)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    async def get_messages(self, chat_id: str, limit: int) -> list[ChatMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM (
                    SELECT id, role, content
                    FROM chat_messages
                    WHERE chat_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (chat_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def add_message(self, chat_id: str, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO chat_messages (chat_id, role, content) VALUES (?, ?, ?)",
                (chat_id, role, content),
            )

    async def trim_messages(self, chat_id: str, max_messages: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM chat_messages
                WHERE chat_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM chat_messages
                      WHERE chat_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
                """,
                (chat_id, chat_id, max_messages),
            )

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id_id
                ON chat_messages (chat_id, id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parse_sqlite_url(database_url: str) -> Path:
        if database_url.startswith("sqlite:///"):
            return Path(database_url.removeprefix("sqlite:///"))
        return Path(database_url)
