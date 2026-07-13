# AsyncIterator 是异步逐项产出值的协议，类似 Java Reactor 的 Flux<String>。
from collections.abc import AsyncIterator

# 读取全局配置以决定记忆实现和记忆窗口大小。
from app.core.config import get_settings
from app.memory.chat_memory import ChatMemory, DatabaseChatMemory, InMemoryChatMemory
from app.services.llm_client import LLMClient


# system 角色消息会固定放在每轮对话最前面，用于约束模型人设与行为边界。
SYSTEM_PROMPT = "扮演深耕恋爱心理领域的专家。开场向用户表明身份，告知用户可倾诉恋爱难题。"


class ChatService:
    """聊天业务服务。

    Java 开发者对照：这个类对应 Java 项目里的 `LoveApp`。系统提示词、会话记忆、
    RAG、工具调用等业务能力都应该放在这里，API 路由保持像 Spring Controller 一样薄。
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        chat_memory: ChatMemory | None = None,
        max_messages: int | None = None,
    ) -> None:
        """支持测试时注入依赖，类似 Java 里的构造器注入。"""
        # 先取得缓存配置，随后允许传入参数覆盖默认依赖，便于单元测试。
        settings = get_settings()
        # Python 的 or 实现“有注入用注入，否则新建”，对应 Java 构造器注入的默认装配。
        self.llm_client = llm_client or LLMClient()
        self.chat_memory = chat_memory or self._create_chat_memory(
            memory_type=settings.chat_memory_type,
            database_url=settings.database_url,
        )
        # 会话窗口上限防止历史无限增长并挤占模型上下文与调用成本。
        self.max_messages = max_messages or settings.chat_memory_max_messages

    async def chat(self, message: str, chat_id: str = "default") -> str:
        """加载会话记忆，调用模型，再保存当前轮次。"""
        # 组装 system、历史和本轮 user 消息，形成 OpenAI-compatible messages 数组。
        messages = await self._build_messages(message, chat_id)
        # 非流式调用等待完整回答后才继续。
        answer = await self.llm_client.chat(messages)

        # 仅当模型成功返回后写入用户和助手消息，避免留下半轮脏数据。
        await self._save_turn(chat_id, message, answer)
        return answer

    async def stream_chat(self, message: str, chat_id: str = "default") -> AsyncIterator[str]:
        """加载会话记忆，流式调用模型，并在结束后保存完整回复。"""
        messages = await self._build_messages(message, chat_id)

        # 生成器执行到 yield 会暂停；消费完流后才继续保存完整答案。
        # 收集片段用于流结束后写入一条完整 assistant 历史消息。
        answer_chunks: list[str] = []
        async for chunk in self.llm_client.stream_chat(messages):
            # 同一片段既缓存又立即 yield，实现“前端实时显示、后端完整记忆”。
            answer_chunks.append(chunk)
            yield chunk

        await self._save_turn(chat_id, message, "".join(answer_chunks))

    async def _build_messages(self, message: str, chat_id: str) -> list[dict[str, str]]:
        # *history 是可迭代解包，作用类似 Java Stream.concat 后 collect 成新列表。
        # 记忆实现已按窗口读取最近消息，避免把全部历史都发给模型。
        history = await self.chat_memory.get_messages(chat_id, limit=self.max_messages)
        return [
            # OpenAI Chat Completions 约定每条消息含 role 和 content。
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": message},
        ]

    async def _save_turn(self, chat_id: str, message: str, answer: str) -> None:
        # 先保存用户输入，再保存回答，保证数据库读取时的对话顺序自然。
        await self.chat_memory.add_message(chat_id, "user", message)
        await self.chat_memory.add_message(chat_id, "assistant", answer)
        # 写入后裁剪，保证内存和数据库中的每个会话都不会无限增长。
        await self.chat_memory.trim_messages(chat_id, self.max_messages)

    @staticmethod
    def _create_chat_memory(memory_type: str, database_url: str) -> ChatMemory:
        """根据配置创建记忆实现，类似 Spring 根据 profile 注入不同 Bean。"""
        # 目前只有 database 显式选择持久化实现，其他值回退为内存实现。
        if memory_type == "database":
            return DatabaseChatMemory(database_url=database_url)
        return InMemoryChatMemory()
