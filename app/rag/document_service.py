import hashlib

from app.rag.embedding_client import EmbeddingClient
from app.rag.schemas import ChunkToStore, DocumentStatus
from app.rag.splitter import TextSplitter
from app.rag.vector_store import PgVectorStore


class DocumentProcessingError(Exception):
    """文档处理失败。"""


class DocumentService:
    """编排文本切块、向量化与 pgvector 入库。"""

    def __init__(
        self,
        vector_store: PgVectorStore,
        embedding_client: EmbeddingClient,
        splitter: TextSplitter | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_client = embedding_client
        self.splitter = splitter or TextSplitter()

    async def ingest_text(
        self,
        knowledge_base_id: str,
        source_name: str,
        raw_content: str,
        version: int = 1,
    ) -> str:
        """将一篇纯文本文档处理并写入知识库。"""

        normalized_content = raw_content.strip()
        if not normalized_content:
            raise ValueError("Document content must not be blank.")

        content_hash = hashlib.sha256(
            normalized_content.encode("utf-8")
        ).hexdigest()

        document_id = await self.vector_store.create_document(
            knowledge_base_id=knowledge_base_id,
            source_name=source_name,
            content_hash=content_hash,
            raw_content=normalized_content,
            version=version,
        )

        try:
            await self.vector_store.update_document_status(
                document_id=document_id,
                status=DocumentStatus.PROCESSING,
            )

            text_chunks = self.splitter.split(normalized_content)
            if not text_chunks:
                raise DocumentProcessingError("Document produced no chunks.")

            embeddings = await self.embedding_client.embed(
                [chunk.content for chunk in text_chunks]
            )

            if len(embeddings) != len(text_chunks):
                raise DocumentProcessingError(
                    "Embedding provider returned an unexpected vector count."
                )

            chunks_to_store = [
                ChunkToStore(
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=embedding,
                    metadata={
                        "startChar": chunk.start_char,
                        "endChar": chunk.end_char,
                    },
                )
                for chunk, embedding in zip(text_chunks, embeddings, strict=True)
            ]

            await self.vector_store.replace_chunks(
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                chunks=chunks_to_store,
            )

            await self.vector_store.update_document_status(
                document_id=document_id,
                status=DocumentStatus.READY,
            )

            return document_id

        except Exception as exc:
            await self.vector_store.update_document_status(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                error_message="Document processing failed.",
            )
            raise DocumentProcessingError(
                f"Failed to process document: {source_name}"
            ) from exc