from typing import Literal
from pydantic import BaseModel, Field

class IntentClassification(BaseModel):
    intent: Literal["query_order", "query_weather", "chat", "unknown"]
    confidence: float = Field(ge=0, le=1)
    entities: dict[str, str] = Field(default_factory=dict)