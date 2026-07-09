from app.core.config import get_settings
from app.memory.chat_memory import ChatMemory, DatabaseChatMemory, InMemoryChatMemory
from app.services.llm_client import LLMClient


SYSTEM_PROMPT = "扮演深耕恋爱心理领域的专家。开场向用户表明身份，告知用户可倾诉恋爱难题。"


class ChatService:
    """Business service for chat use cases.

    For Java developers: this is the Python counterpart of `LoveApp`. It is the
    right place to add system prompts, memory, RAG, or tools later, while the API
    router stays thin like a Spring `Controller`.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        chat_memory: ChatMemory | None = None,
        max_messages: int | None = None,
    ) -> None:
        """Accept optional dependencies for tests, similar to constructor injection."""
        settings = get_settings()
        self.llm_client = llm_client or LLMClient()
        self.chat_memory = chat_memory or self._create_chat_memory(
            memory_type=settings.chat_memory_type,
            database_url=settings.database_url,
        )
        self.max_messages = max_messages or settings.chat_memory_max_messages

    async def chat(self, message: str, chat_id: str = "default") -> str:
        """Load conversation memory, call the model, then save the new turn."""
        history = await self.chat_memory.get_messages(chat_id, limit=self.max_messages)
        # Java 对照：这里等价于 defaultSystem(SYSTEM_PROMPT) + MessageWindowChatMemory。
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": message},
        ]
        answer = await self.llm_client.chat(messages)

        await self.chat_memory.add_message(chat_id, "user", message)
        await self.chat_memory.add_message(chat_id, "assistant", answer)
        await self.chat_memory.trim_messages(chat_id, self.max_messages)

        return answer

    @staticmethod
    def _create_chat_memory(memory_type: str, database_url: str) -> ChatMemory:
        """根据配置创建记忆实现，类似 Spring 根据 profile 注入不同 Bean。"""
        if memory_type == "database":
            return DatabaseChatMemory(database_url=database_url)
        return InMemoryChatMemory()
