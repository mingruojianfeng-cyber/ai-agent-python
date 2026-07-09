from typing import Literal

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """Structured output DTO for later intent classification steps.

    For Java developers: this is like a Java record returned by
    `chatClient.call().entity(IntentClassification.class)`, with Pydantic doing
    runtime validation.
    """

    intent: Literal["query_order", "query_weather", "chat", "unknown"]
    confidence: float = Field(ge=0, le=1)
    entities: dict[str, str] = Field(default_factory=dict)
