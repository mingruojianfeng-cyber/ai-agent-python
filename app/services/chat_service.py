from app.services.llm_client import LLMClient


class ChatService:
    """Business service for chat use cases.

    For Java developers: this is the Python counterpart of `LoveApp`. It is the
    right place to add system prompts, memory, RAG, or tools later, while the API
    router stays thin like a Spring `Controller`.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """Accept an optional client for tests, similar to constructor injection."""
        self.llm_client = llm_client or LLMClient()

    async def chat(self, message: str) -> str:
        """Convert a plain user message into model messages and call LLMClient."""
        messages = [{"role": "user", "content": message}]
        return await self.llm_client.chat(messages)
