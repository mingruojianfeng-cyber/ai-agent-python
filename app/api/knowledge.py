from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.rag.document_service import DocumentProcessingError, DocumentService
from app.rag.embedding_client import EmbeddingClient
from app.rag.knowledge_service import KnowledgeService
from app.rag.schemas import DocumentStatus
from app.rag.vector_store import PgVectorStore
from app.schemas.knowledge import (
    DocumentImportResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    TextDocumentImportRequest,
)


router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    """创建进程内复用的知识库服务。"""

    settings = get_settings()

    if not settings.rag_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG is disabled. Set RAG_ENABLED=true first.",
        )

    if not settings.database_url.startswith("postgresql+asyncpg://"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG requires a PostgreSQL asyncpg DATABASE_URL.",
        )

    vector_store = PgVectorStore(
        database_url=settings.database_url,
        embedding_dimensions=settings.embedding_dimensions,
    )

    embedding_client = EmbeddingClient(settings=settings)

    document_service = DocumentService(
        vector_store=vector_store,
        embedding_client=embedding_client,
    )

    return KnowledgeService(
        vector_store=vector_store,
        document_service=document_service,
    )


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgeBaseResponse:
    """创建一个空知识库。"""

    knowledge_base_id = await service.create_knowledge_base(
        name=request.name,
        description=request.description,
    )

    return KnowledgeBaseResponse(
        id=knowledge_base_id,
        name=request.name.strip(),
        description=request.description.strip(),
    )


@router.post(
    "/{knowledge_base_id}/documents/import",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_text_document(
    knowledge_base_id: UUID,
    request: TextDocumentImportRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> DocumentImportResponse:
    """同步导入一篇纯文本并完成向量化。"""

    try:
        document_id = await service.import_text_document(
            knowledge_base_id=str(knowledge_base_id),
            source_name=request.source_name,
            content=request.content,
            version=request.version,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The same document version or content already exists.",
        ) from exc
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document embedding or processing failed.",
        ) from exc

    return DocumentImportResponse(
        documentId=document_id,
        status=DocumentStatus.READY,
    )