import pytest

from app.schemas.intent import IntentClassification
from app.services.intent_service import IntentClassificationError, IntentService


class FakeJsonLLMClient:
    def __init__(self, answers: list[str]) -> None:
        self.answers = answers
        self.messages_history: list[list[dict[str, str]]] = []

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        self.messages_history.append(messages)
        return self.answers.pop(0)


@pytest.mark.asyncio
async def test_intent_service_classifies_message_with_structured_output() -> None:
    service = IntentService(
        llm_client=FakeJsonLLMClient(
            [
                (
                    '{"intent":"rag_search","confidence":0.91,'
                    '"entities":{"keyword":"postgresql 对话记忆"}}'
                )
            ]
        )
    )

    result = await service.classify("帮我检索 postgresql 对话记忆")

    assert isinstance(result, IntentClassification)
    assert result.intent == "rag_search"
    assert result.confidence == 0.91
    assert result.entities == {"keyword": "postgresql 对话记忆"}


@pytest.mark.asyncio
async def test_intent_service_retries_once_when_json_schema_is_invalid() -> None:
    service = IntentService(
        llm_client=FakeJsonLLMClient(
            [
                '{"intent":"delete_database","confidence":1.2,"entities":{}}',
                '{"intent":"tool_call","confidence":0.82,"entities":{"tool":"weather"}}',
            ]
        )
    )

    result = await service.classify("调用天气工具")

    assert result.intent == "tool_call"
    assert len(service.llm_client.messages_history) == 2


@pytest.mark.asyncio
async def test_intent_service_raises_business_error_after_retry_failed() -> None:
    service = IntentService(
        llm_client=FakeJsonLLMClient(
            [
                '{"intent":"bad","confidence":0.4,"entities":{}}',
                '{"intent":"still_bad","confidence":0.4,"entities":{}}',
            ]
        )
    )

    with pytest.raises(IntentClassificationError):
        await service.classify("随便聊聊")
