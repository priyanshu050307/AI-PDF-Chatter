import asyncio
import time
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.retrieval import (
    RetrievalResult,
    RetrievalTelemetry,
    RetrievalDebugResponse,
)
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.fusion_service import FusionService
from app.services.retrieval.reranker_service import get_reranker
from app.core.config import settings
from app.core.logging import logger


class HybridRetrievalPipeline:
    """
    Modular Phase 8 Advanced Hybrid Retrieval Pipeline.
    Orchestrates Parallel Search (Dense Vector + Lexical Full-Text Search),
    Reciprocal Rank Fusion (RRF), Deduplication, Reranking, and Telemetry.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dense_retriever = DenseRetriever(db)
        self.lexical_retriever = LexicalRetriever(db)
        self.fusion_service = FusionService(rrf_k=settings.RRF_K)
        self.reranker = get_reranker()

    async def execute_pipeline(
        self,
        document_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        selected_text: Optional[str] = None
    ) -> Tuple[List[RetrievalResult], RetrievalTelemetry]:
        start_total = time.perf_counter()

        # 1. Query Normalization
        clean_query, tech_tokens = self.lexical_retriever.normalize_query(query or "")
        effective_query = clean_query if clean_query else (selected_text or "")

        # 2. Parallel Dense & Lexical Retrieval
        dense_k = settings.DENSE_TOP_K
        lexical_k = settings.LEXICAL_TOP_K

        t_dense_start = time.perf_counter()
        dense_task = asyncio.create_task(
            self.dense_retriever.retrieve(document_id, query, top_k=dense_k, selected_text=selected_text)
        )

        t_lex_start = time.perf_counter()
        lexical_task = asyncio.create_task(
            self.lexical_retriever.retrieve(document_id, query, top_k=lexical_k, selected_text=selected_text)
        )

        dense_candidates, lexical_candidates = await asyncio.gather(dense_task, lexical_task)
        dense_latency = (time.perf_counter() - t_dense_start) * 1000.0
        lexical_latency = (time.perf_counter() - t_lex_start) * 1000.0

        # 3. Candidate Fusion (RRF) & Deduplication
        t_fusion_start = time.perf_counter()
        if settings.ENABLE_HYBRID_RETRIEVAL:
            fused_candidates = self.fusion_service.fuse_and_deduplicate(dense_candidates, lexical_candidates)
        else:
            fused_candidates = dense_candidates
        fusion_latency = (time.perf_counter() - t_fusion_start) * 1000.0

        # 4. Reranking
        t_rerank_start = time.perf_counter()
        rerank_k = settings.RERANK_TOP_K
        candidates_to_rerank = fused_candidates[:rerank_k]

        if settings.ENABLE_RERANKING and candidates_to_rerank:
            final_evidence = await self.reranker.rerank(
                query=effective_query,
                candidates=candidates_to_rerank,
                top_k=top_k
            )
        else:
            final_evidence = candidates_to_rerank[:top_k]

        rerank_latency = (time.perf_counter() - t_rerank_start) * 1000.0

        # 5. Relevance Threshold Filtering (if configured)
        if settings.RETRIEVAL_MIN_SCORE_THRESHOLD > 0.0:
            final_evidence = [
                item for item in final_evidence
                if (item.rerank_score or item.fused_score or item.dense_score or 0.0) >= settings.RETRIEVAL_MIN_SCORE_THRESHOLD
            ]

        total_latency = (time.perf_counter() - start_total) * 1000.0

        # 6. Telemetry Logging
        telemetry = RetrievalTelemetry(
            pipeline_version=settings.RETRIEVAL_PIPELINE_VERSION,
            query=effective_query,
            document_id=str(document_id),
            dense_candidate_count=len(dense_candidates),
            lexical_candidate_count=len(lexical_candidates),
            fused_candidate_count=len(fused_candidates),
            reranked_count=len(candidates_to_rerank),
            final_count=len(final_evidence),
            dense_latency_ms=round(dense_latency, 2),
            lexical_latency_ms=round(lexical_latency, 2),
            fusion_latency_ms=round(fusion_latency, 2),
            rerank_latency_ms=round(rerank_latency, 2),
            total_retrieval_latency_ms=round(total_latency, 2),
        )

        logger.info(
            f"[Phase 8 Telemetry] doc={document_id} query='{effective_query[:30]}' "
            f"dense={len(dense_candidates)} lex={len(lexical_candidates)} fused={len(fused_candidates)} "
            f"final={len(final_evidence)} total_time={total_latency:.1f}ms"
        )

        return final_evidence, telemetry

    async def debug_pipeline(
        self,
        document_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        selected_text: Optional[str] = None
    ) -> RetrievalDebugResponse:
        """Full pipeline execution returning all intermediate candidate states for debug inspection."""
        clean_query, tech_tokens = self.lexical_retriever.normalize_query(query or "")
        effective_query = clean_query if clean_query else (selected_text or "")

        dense_candidates = await self.dense_retriever.retrieve(
            document_id, query, top_k=settings.DENSE_TOP_K, selected_text=selected_text
        )
        lexical_candidates = await self.lexical_retriever.retrieve(
            document_id, query, top_k=settings.LEXICAL_TOP_K, selected_text=selected_text
        )
        fused_candidates = self.fusion_service.fuse_and_deduplicate(dense_candidates, lexical_candidates)

        final_evidence, telemetry = await self.execute_pipeline(
            document_id=document_id, query=query, top_k=top_k, selected_text=selected_text
        )

        return RetrievalDebugResponse(
            query=query or "",
            normalized_query=effective_query,
            document_id=str(document_id),
            pipeline_version=settings.RETRIEVAL_PIPELINE_VERSION,
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            fused_candidates=fused_candidates,
            final_evidence=final_evidence,
            telemetry=telemetry
        )
