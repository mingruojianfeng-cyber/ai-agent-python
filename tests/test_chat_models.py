import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.intent import IntentClassification


def test_chat_request_uses_default_chat_id() -> None:
    request = ChatRequest(message="你好")

    assert request.message == "你好"
    assert request.chat_id == "default"


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_response_contains_answer() -> None:
    response = ChatResponse(answer="你好，我是 AI 助手")

    assert response.answer == "你好，我是 AI 助手"


def test_intent_classification_accepts_valid_intent() -> None:
    result = IntentClassification(
        intent="query_order",
        confidence=0.92,
        entities={"order_id": "12345"},
    )

    assert result.intent == "query_order"
    assert result.confidence == 0.92
    assert result.entities["order_id"] == "12345"


def test_intent_classification_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        IntentClassification(
            intent="query_order",
            confidence=1.5,
            entities={},
        )


def test_intent_classification_rejects_unknown_intent_value() -> None:
    with pytest.raises(ValidationError):
        IntentClassification(
            intent="delete_database",
            confidence=0.8,
            entities={},
        )