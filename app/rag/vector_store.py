import json
import math
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.rag.schemas import ChunkToStore, RetrievedChunk


class PgVectorStore:
    """PostgreSQL + pgvector 的最小存储实现。"""

    def __init__(
        self,
        database_url: str,
        embedding_dimensions: int,
        engine: AsyncEngine | None = None,
    ) -> None:
        self.embedding_dimensions = embedding_dimensions
        self.engine = engine or create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_knowledge_base(self, name: str, description: str = "") -> str:
        query = text(
            """
            INSERT INTO knowledge_bases (name, description)
            VALUES (:name, :description)
            RETURNING id::text AS id
            """
        )

        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    query,
                    {"name": name, "description": description},
                )
                return result.mappings().one()["id"]

    async def create_document(
        self,
        knowledge_base_id: str,
        source_name: str,
        content_hash: str,
        raw_content: str,
        version: int = 1,
    ) -> str:
        query = text(
            """
            INSERT INTO documents (
                knowledge_base_id,
                source_name,
                content_hash,
                version,
                status,
                raw_content
            )
            VALUES (
                CAST(:knowledge_base_id AS uuid),
                :source_name,
                :content_hash,
                :version,
                'PENDING',
                :raw_content
            )
            RETURNING id::text AS id
            """
        )

        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    query,
                    {
                        "knowledge_base_id": knowledge_base_id,
                        "source_name": source_name,
                        "content_hash": content_hash,
                        "version": version,
                        "raw_content": raw_content,
                    },
                )
                return result.mappings().one()["id"]

    async def replace_chunks(
        self,
        knowledge_base_id: str,
        document_id: str,
        chunks: Sequence[ChunkToStore],
    ) -> None:
        self._validate_chunks(chunks)

        delete_query = text(
            """
            DELETE FROM document_chunks
            WHERE document_id = CAST(:document_id AS uuid)
            """
        )

        insert_query = text(
            """
            INSERT INTO document_chunks (
                knowledge_base_id,
                document_id,
                chunk_index,
                content,
                embedding,
                metadata
            )
            VALUES (
                CAST(:knowledge_base_id AS uuid),
                CAST(:document_id AS uuid),
                :chunk_index,
                :content,
                CAST(:embedding AS halfvec),
                CAST(:metadata AS jsonb)
            )
            """
        )

        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(delete_query, {"document_id": document_id})

                for chunk in chunks:
                    await session.execute(
                        insert_query,
                        {
                            "knowledge_base_id": knowledge_base_id,
                            "document_id": document_id,
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "embedding": self._to_vector_literal(chunk.embedding),
                            "metadata": json.dumps(chunk.metadata, ensure_ascii=False),
                        },
                    )


    async def search_vector(
        self,
        knowledge_base_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """在指定知识库中执行 pgvector 余弦距离 Top-K 检索。"""

        if not 1 <= limit <= 20:
            raise ValueError("Search limit must be between 1 and 20.")

        if len(query_embedding) != self.embedding_dimensions:
            raise ValueError(
                f"Query embedding dimension must be {self.embedding_dimensions}, "
                f"got {len(query_embedding)}."
            )

        if not all(math.isfinite(value) for value in query_embedding):
            raise ValueError("Query embedding contains non-finite values.")

        query = text(
            """
            SELECT
                chunks.id::text AS chunk_id,
                chunks.knowledge_base_id::text AS knowledge_base_id,
                chunks.document_id::text AS document_id,
                documents.source_name AS document_name,
                chunks.chunk_index,
                chunks.content,
                chunks.metadata,
                LEAST(
                    1.0,
                    GREATEST(
                        0.0,
                        1 - (
                            chunks.embedding <=> CAST(:query_embedding AS halfvec)
                        )
                    )
                ) AS score
            FROM document_chunks AS chunks
            INNER JOIN documents
                ON documents.id = chunks.document_id
            WHERE chunks.knowledge_base_id = CAST(:knowledge_base_id AS uuid)
              AND documents.status = 'READY'
            ORDER BY chunks.embedding <=> CAST(:query_embedding AS halfvec)
            LIMIT :limit
            """
        )

        async with self.session_factory() as session:
            result = await session.execute(
                query,
                {
                    "knowledge_base_id": knowledge_base_id,
                    "query_embedding": self._to_vector_literal(query_embedding),
                    "limit": limit,
                },
            )

        return [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                knowledge_base_id=row.knowledge_base_id,
                document_id=row.document_id,
                document_name=row.document_name,
                chunk_index=row.chunk_index,
                content=row.content,
                score=float(row.score),
                metadata=row.metadata or {},
            )
            for row in result.mappings().all()
        ]

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        query = text(
            """
            UPDATE documents
            SET status = :status,
                error_message = :error_message,
                updated_at = NOW()
            WHERE id = CAST(:document_id AS uuid)
            """
        )

        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    query,
                    {
                        "document_id": document_id,
                        "status": status,
                        "error_message": error_message,
                    },
                )

    async def close(self) -> None:
        await self.engine.dispose()

    def _validate_chunks(self, chunks: Sequence[ChunkToStore]) -> None:
        for chunk in chunks:
            if len(chunk.embedding) != self.embedding_dimensions:
                raise ValueError(
                    f"Embedding dimension must be {self.embedding_dimensions}, "
                    f"got {len(chunk.embedding)}."
                )

            if not all(math.isfinite(value) for value in chunk.embedding):
                raise ValueError("Embedding contains non-finite values.")

    @staticmethod
    def _to_vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(str(value) for value in vector) + "]"
