import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import get_chat_service
from app.main import app
from app.services.chat_service import ChatService
from app.services.llm_client import LLMClientError


SYSTEM_PROMPT = "扮演深耕恋爱心理领域的专家。开场向用户表明身份，告知用户可倾诉恋爱难题。"


class FakeLLMClient:
    def __init__(self) -> None:
        self.messages = None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "model answer"


@pytest.mark.asyncio
async def test_chat_endpoint_returns_model_answer() -> None:
    fake_llm_client = FakeLLMClient()

    app.dependency_overrides[get_chat_service] = lambda: ChatService(llm_client=fake_llm_client)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "你好", "chatId": "demo"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"answer": "model answer"}
    assert fake_llm_client.messages == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "你好"},
    ]


@pytest.mark.asyncio
async def test_chat_endpoint_returns_502_when_model_provider_fails() -> None:
    class FailingLLMClient:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            raise LLMClientError("boom")

    app.dependency_overrides[get_chat_service] = lambda: ChatService(llm_client=FailingLLMClient())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "你好", "chatId": "demo"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Model provider request failed."}
