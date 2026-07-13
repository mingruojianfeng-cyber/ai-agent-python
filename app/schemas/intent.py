# Literal 将字段限制为有限字符串集合，效果类似 Java enum 的可选值约束。
from typing import Literal

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """面向后续 Agent 编排的结构化意图识别结果。"""

    # 只有这些意图可通过 Pydantic 校验，模型乱填新字符串会被识别为无效输出。
    intent: Literal["rag_search", "tool_call", "mcp_call", "yuagent_handoff", "chat", "unknown"]
    # 置信度限定在闭区间 [0, 1]，避免供应商返回无意义的概率值。
    confidence: float = Field(ge=0, le=1)
    # default_factory 每次创建新字典，避免可变默认值被多个请求共享。
    entities: dict[str, str] = Field(default_factory=dict)

    # Literal 约束允许的字符串集合，类似 Java enum；Pydantic 会在反序列化时校验它。
