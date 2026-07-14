from pydantic import BaseModel, ConfigDict, Field

from app.rag.schemas import DocumentStatus


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求。"""

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1000)


class KnowledgeBaseResponse(BaseModel):
    """知识库响应。"""

    id: str
    name: str
    description: str


class TextDocumentImportRequest(BaseModel):
    """导入纯文本文档请求。"""

    source_name: str = Field(
        min_length=1,
        max_length=512,
        alias="sourceName",
    )
    content: str = Field(min_length=1, max_length=2_000_000)
    version: int = Field(default=1, ge=1)

    model_config = ConfigDict(populate_by_name=True)


class DocumentImportResponse(BaseModel):
    """文档导入完成后的响应。"""

    document_id: str = Field(alias="documentId")
    status: DocumentStatus

    model_config = ConfigDict(populate_by_name=True)