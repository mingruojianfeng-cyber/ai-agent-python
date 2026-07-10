import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import get_chat_service
from app.main import app
from app.memory.chat_memory import InMemoryChatMemory
from app.schemas.intent import IntentClassification
from app.services.chat_service import ChatService
from app.services.intent_service import IntentClassificationError
from app.services.llm_client import LLMClientError


SYSTEM_PROMPT = "扮演深耕恋爱心理领域的专家。开场向用户表明身份，告知用户可倾诉恋爱难题。"


class FakeLLMClient:
    def __init__(self) -> None:
        self.messages = None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "model answer"


class FakeChatService:
    def __init__(self) -> None:
        self.message = None
        self.chat_id = None

    async def chat(self, message: str, chat_id: str) -> str:
        self.message = message
        self.chat_id = chat_id
        return "service answer"

    async def stream_chat(self, message: str, chat_id: str):
        self.message = message
        self.chat_id = chat_id
        for chunk in ["hello", " stream"]:
            yield chunk


class FakeIntentService:
    def __init__(self, result: IntentClassification | None = None, should_fail: bool = False) -> None:
        self.result = result or IntentClassification(intent="chat", confidence=0.7, entities={})
        self.should_fail = should_fail
        self.message = None

    async def classify(self, message: str) -> IntentClassification:
        self.message = message
        if self.should_fail:
            raise IntentClassificationError("bad structured output")
        return self.result


@pytest.mark.asyncio
async def test_chat_endpoint_returns_model_answer() -> None:
    fake_llm_client = FakeLLMClient()

    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        llm_client=fake_llm_client,
        chat_memory=InMemoryChatMemory(),
    )
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
async def test_chat_endpoint_passes_chat_id_to_service() -> None:
    fake_service = FakeChatService()

    app.dependency_overrides[get_chat_service] = lambda: fake_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "你好", "chatId": "chat-123"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"answer": "service answer"}
    assert fake_service.message == "你好"
    assert fake_service.chat_id == "chat-123"


@pytest.mark.asyncio
async def test_chat_stream_endpoint_returns_sse_chunks() -> None:
    fake_service = FakeChatService()

    app.dependency_overrides[get_chat_service] = lambda: fake_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/chat/stream",
                json={"message": "你好", "chatId": "chat-stream-123"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "data: hello\n\ndata:  stream\n\n"
    assert fake_service.message == "你好"
    assert fake_service.chat_id == "chat-stream-123"


@pytest.mark.asyncio
async def test_classify_intent_endpoint_returns_structured_intent() -> None:
    from app.api.chat import get_intent_service

    fake_service = FakeIntentService(
        IntentClassification(
            intent="rag_search",
            confidence=0.93,
            entities={"keyword": "postgresql 对话记忆"},
        )
    )

    app.dependency_overrides[get_intent_service] = lambda: fake_service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/classify-intent",
                json={"message": "帮我检索 postgresql 对话记忆"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "intent": "rag_search",
        "confidence": 0.93,
        "entities": {"keyword": "postgresql 对话记忆"},
    }
    assert fake_service.message == "帮我检索 postgresql 对话记忆"


@pytest.mark.asyncio
async def test_classify_intent_endpoint_returns_422_for_invalid_structured_output() -> None:
    from app.api.chat import get_intent_service

    app.dependency_overrides[get_intent_service] = lambda: FakeIntentService(should_fail=True)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/classify-intent", json={"message": "未知任务"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Model structured output parse failed."}


def test_get_chat_service_reuses_default_service_instance(monkeypatch) -> None:
    class CachedService:
        pass

    get_chat_service.cache_clear()
    monkeypatch.setattr("app.api.chat.ChatService", CachedService)

    first_service = get_chat_service()
    second_service = get_chat_service()

    assert first_service is second_service
    get_chat_service.cache_clear()


def test_get_intent_service_reuses_default_service_instance(monkeypatch) -> None:
    from app.api.chat import get_intent_service

    class CachedIntentService:
        pass

    get_intent_service.cache_clear()
    monkeypatch.setattr("app.api.chat.IntentService", CachedIntentService)

    first_service = get_intent_service()
    second_service = get_intent_service()

    assert first_service is second_service
    get_intent_service.cache_clear()


@pytest.mark.asyncio
async def test_chat_endpoint_returns_502_when_model_provider_fails() -> None:
    class FailingLLMClient:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            raise LLMClientError("boom")

    app.dependency_overrides[get_chat_service] = lambda: ChatService(
        llm_client=FailingLLMClient(),
        chat_memory=InMemoryChatMemory(),
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "你好", "chatId": "demo"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Model provider request failed."}
