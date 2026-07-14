from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# 枚举
class DocumentStatus(StrEnum):
    """文档入库生命周期状态。PENDING → PROCESSING → READY / FAILED：后面异步导入接口会按这个状态流转。"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class RetrievedChunk(BaseModel):
    """检索返回给chatService的文档块"""

    # 检索结果生成后不能被下游代码悄悄修改。
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    knowledge_base_id: str
    document_id: str
    document_name: str
    chunk_index: int = Field(ge=0)
    content: str
    score: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkToStore(BaseModel):
    """待写入 pgvector 的文档分块。"""

    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSource(BaseModel):
    """回答中实际引用的知识库来源。"""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    document_id: str = Field(alias="documentId")
    document_name: str = Field(alias="documentName")
    chunk_index: int = Field(alias="chunkIndex", ge=0)
    score: float = Field(ge=0, le=1)