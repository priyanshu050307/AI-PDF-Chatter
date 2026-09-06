import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.schemas.retrieval import RetrievalResult


class RetrievalService(ABC):
    """Abstract interface boundary for RAG vector & hybrid retrieval."""

    @abstractmethod
    async def retrieve_relevant_chunks(
        self,
        document_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        selected_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve top K relevant chunks for a document query."""
        pass


class PgVectorRetrievalService(RetrievalService):
    """
    Phase 8 Advanced Hybrid Retrieval Service Implementation.
    Delegates to HybridRetrievalPipeline (Parallel Dense + Lexical Search, RRF Fusion, and Reranking).
    Maintains 100% contract compatibility with RAGService, ContextBuilder, and TutorService.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pipeline = HybridRetrievalPipeline(db)

    async def retrieve_relevant_chunks(
        self,
        document_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        selected_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        final_results, _telemetry = await self.pipeline.execute_pipeline(
            document_id=document_id,
            query=query,
            top_k=top_k,
            selected_text=selected_text
        )

        # Convert typed RetrievalResult objects to dict format expected by ContextBuilder
        output_dicts: List[Dict[str, Any]] = []
        for item in final_results:
            score = item.rerank_score or item.fused_score or item.dense_score or 0.0
            output_dicts.append({
                "chunk_id": item.chunk_id,
                "content": item.content,
                "score": score,
                "document_id": item.document_id,
                "page_start": item.page_start,
                "page_end": item.page_end,
                "chapter_title": item.chapter_title,
                "section_title": item.section_title,
                "token_count": item.token_count,
            })

        return output_dicts
