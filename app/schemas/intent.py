from typing import Literal

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """面向后续 Agent 编排的结构化意图识别结果。"""

    intent: Literal["rag_search", "tool_call", "mcp_call", "yuagent_handoff", "chat", "unknown"]
    confidence: float = Field(ge=0, le=1)
    entities: dict[str, str] = Field(default_factory=dict)
