import pytest

from app.core.config import Settings
from app.services.llm_client import LLMClient


class FakeMessage:
    content = "hello from model"


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    choices = [FakeChoice()]


class FakeDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class FakeStreamChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = FakeDelta(content)


class FakeStreamChunk:
    def __init__(self, content: str | None) -> None:
        self.choices = [FakeStreamChoice(content)]


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if kwargs["stream"]:
            return self._stream()
        return FakeCompletion()

    async def _stream(self):
        for content in ["hello", None, " stream"]:
            yield FakeStreamChunk(content)


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeOpenAICompatibleClient:
    def __init__(self, *, api_key: str, base_url: str, timeout: float) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.chat = FakeChat()


def test_llm_client_uses_openai_compatible_settings() -> None:
    created_clients: list[FakeOpenAICompatibleClient] = []

    def client_factory(**kwargs) -> FakeOpenAICompatibleClient:
        client = FakeOpenAICompatibleClient(**kwargs)
        created_clients.append(client)
        return client

    settings = Settings(
        llm_provider="deepseek",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="sk-deepseek",
        llm_model="deepseek-chat",
        request_timeout_seconds=30,
    )

    client = LLMClient(settings=settings, client_factory=client_factory)

    assert created_clients[0].api_key == "sk-deepseek"
    assert created_clients[0].base_url == "https://api.deepseek.com"
    assert created_clients[0].timeout == 30
    assert client.provider == "deepseek"


@pytest.mark.asyncio
async def test_chat_sends_messages_and_returns_first_choice_content() -> None:
    settings = Settings(
        llm_provider="deepseek",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="sk-deepseek",
        llm_model="deepseek-chat",
        llm_reasoning_effort="",
        llm_extra_body_json="",
    )
    fake_client = FakeOpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.request_timeout_seconds,
    )
    client = LLMClient(settings=settings, client_factory=lambda **_: fake_client)

    answer = await client.chat([{"role": "user", "content": "Hello"}])

    assert answer == "hello from model"
    assert fake_client.chat.completions.kwargs == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }


@pytest.mark.asyncio
async def test_chat_json_requests_json_object_response() -> None:
    settings = Settings(
        llm_provider="deepseek",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="sk-deepseek",
        llm_model="deepseek-chat",
        llm_reasoning_effort="",
        llm_extra_body_json="",
    )
    fake_client = FakeOpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.request_timeout_seconds,
    )
    client = LLMClient(settings=settings, client_factory=lambda **_: fake_client)

    answer = await client.chat_json([{"role": "user", "content": "只返回 JSON"}])

    assert answer == "hello from model"
    assert fake_client.chat.completions.kwargs == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "只返回 JSON"}],
        "stream": False,
        "response_format": {"type": "json_object"},
    }


@pytest.mark.asyncio
async def test_stream_chat_sends_stream_request_and_yields_text_chunks() -> None:
    settings = Settings(
        llm_provider="deepseek",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="sk-deepseek",
        llm_model="deepseek-chat",
        llm_reasoning_effort="",
        llm_extra_body_json="",
    )
    fake_client = FakeOpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.request_timeout_seconds,
    )
    client = LLMClient(settings=settings, client_factory=lambda **_: fake_client)

    chunks = [chunk async for chunk in client.stream_chat([{"role": "user", "content": "Hello"}])]

    assert chunks == ["hello", " stream"]
    assert fake_client.chat.completions.kwargs == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }


def test_llm_client_requires_base_url_and_api_key() -> None:
    settings = Settings(llm_base_url="", llm_api_key="")

    with pytest.raises(ValueError, match="LLM_BASE_URL and LLM_API_KEY"):
        LLMClient(settings=settings, client_factory=FakeOpenAICompatibleClient)
