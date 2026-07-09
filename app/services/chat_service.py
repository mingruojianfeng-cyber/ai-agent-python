from app.core.config import get_settings
from app.memory.chat_memory import ChatMemory, DatabaseChatMemory, InMemoryChatMemory
from app.services.llm_client import LLMClient


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
        settings = get_settings()
        self.llm_client = llm_client or LLMClient()
        self.chat_memory = chat_memory or self._create_chat_memory(
            memory_type=settings.chat_memory_type,
            database_url=settings.database_url,
        )
        self.max_messages = max_messages or settings.chat_memory_max_messages

    async def chat(self, message: str, chat_id: str = "default") -> str:
        """加载会话记忆，调用模型，再保存当前轮次。"""
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
