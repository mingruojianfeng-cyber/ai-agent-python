from app.rag.document_service import DocumentService
from app.rag.vector_store import PgVectorStore


class KnowledgeService:
    """知识库领域服务，供 API 路由调用。"""

    def __init__(
        self,
        vector_store: PgVectorStore,
        document_service: DocumentService,
    ) -> None:
        self.vector_store = vector_store
        self.document_service = document_service

    async def create_knowledge_base(
        self,
        name: str,
        description: str,
    ) -> str:
        return await self.vector_store.create_knowledge_base(
            name=name,
            description=description,
        )

    async def import_text_document(
        self,
        knowledge_base_id: str,
        source_name: str,
        content: str,
        version: int,
    ) -> str:
        return await self.document_service.ingest_text(
            knowledge_base_id=knowledge_base_id,
            source_name=source_name,
            raw_content=content,
            version=version,
        )