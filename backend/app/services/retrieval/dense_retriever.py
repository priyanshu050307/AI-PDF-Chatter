import json
import uuid
from typing import List, Optional, Any, Union
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk
from app.schemas.retrieval import RetrievalResult
from app.services.embedding_service import get_embedding_service
from app.core.config import settings
from app.core.logging import logger


class DenseRetriever:
    """
    Dense Vector Similarity Retriever.
    Generates query embeddings and computes vector similarity against document_chunks.
    Supports pgvector / cross-dialect cosine math.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def retrieve(
        self,
        document_id: uuid.UUID,
        query: Any,
        top_k: int = 10,
        selected_text: Optional[str] = None
    ) -> List[RetrievalResult]:
        if isinstance(query, list):
            query_vec = np.array(query, dtype=np.float32)
        else:
            if not query or not str(query).strip():
                if selected_text:
                    retrieval_query = f"Selection context: {selected_text.strip()}"
                else:
                    return []
            else:
                if selected_text:
                    retrieval_query = f"Selection: {selected_text.strip()}\nQuery: {str(query).strip()}"
                else:
                    retrieval_query = str(query).strip()

            # 1. Generate query embedding
            query_embeddings = await self.embedding_service.generate_embeddings([retrieval_query])
            if not query_embeddings:
                return []
            query_vec = np.array(query_embeddings[0], dtype=np.float32)

        # 2. Fetch chunks scoped strictly to document_id
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        all_chunks = list(result.scalars().all())
        chunks = [c for c in all_chunks if c.embedding is not None]

        if not chunks:
            logger.warning(f"No chunks with embeddings found for document {document_id}")
            return []

        # 3. Calculate Cosine Similarity
        scored_results: List[RetrievalResult] = []
        query_norm = np.linalg.norm(query_vec)

        for chunk in chunks:
            raw_emb = chunk.embedding
            if raw_emb is None:
                continue

            if isinstance(raw_emb, str):
                try:
                    raw_emb = json.loads(raw_emb)
                except Exception:
                    continue

            chunk_vec = np.array(raw_emb, dtype=np.float32)
            if len(chunk_vec) != len(query_vec):
                if len(chunk_vec) < len(query_vec):
                    chunk_vec = np.pad(chunk_vec, (0, len(query_vec) - len(chunk_vec)))
                else:
                    chunk_vec = chunk_vec[:len(query_vec)]

            chunk_norm = np.linalg.norm(chunk_vec)

            if query_norm > 0 and chunk_norm > 0:
                sim_score = float(np.dot(query_vec, chunk_vec) / (query_norm * chunk_norm))
            else:
                sim_score = 0.0

            scored_results.append(
                RetrievalResult(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    content=chunk.content,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    chapter_title=chunk.chapter_title,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count or 0,
                    dense_score=round(sim_score, 4),
                )
            )

        # Sort descending by dense_score and return Top-K
        scored_results.sort(key=lambda x: x.dense_score or 0.0, reverse=True)
        return scored_results[:top_k]
