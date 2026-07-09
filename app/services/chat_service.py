from app.services.llm_client import LLMClient


class ChatService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    async def chat(self, message: str) -> str:
        messages = [{"role": "user", "content": message}]
        return await self.llm_client.chat(messages)
