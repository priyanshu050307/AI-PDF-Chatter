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
    Orchestrates Query Classification, Controlled Query Expansion,
    Parallel Search (Dense Vector + Lexical Full-Text Search),
    Reciprocal Rank Fusion (RRF), Deduplication, Reranking, and Telemetry.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dense_retriever = DenseRetriever(db)
        self.lexical_retriever = LexicalRetriever(db)
        self.fusion_service = FusionService(rrf_k=settings.RRF_K)
        self.reranker = get_reranker()

    def classify_query(self, query: str, selected_text: Optional[str] = None) -> str:
        """
        Lightweight deterministic query router:
        - contextual: if active text selection is present
        - technical_identifier: if query contains technical codes (CVE, AES, OAuth, etc.)
        - conceptual: if query is an explanatory or analytical question
        - general: default balanced search
        """
        if selected_text and selected_text.strip():
            return "contextual"

        _clean, tech_tokens = self.lexical_retriever.normalize_query(query or "")
        if tech_tokens:
            return "technical_identifier"

        q_lower = (query or "").lower()
        words = set(q_lower.split())

        table_keywords = {"table", "values", "rows", "columns", "spreadsheet", "tabular"}
        visual_keywords = {"diagram", "figure", "drawing", "picture", "illustration", "chart", "graph"}
        if words.intersection(table_keywords):
            return "table_question"
        if words.intersection(visual_keywords):
            return "visual_question"

        conceptual_keywords = {"why", "how", "explain", "concept", "difference", "overview", "compare", "mechanism"}
        if words.intersection(conceptual_keywords):
            return "conceptual"

        return "general"

    async def execute_pipeline(
        self,
        document_id: Optional[uuid.UUID] = None,
        query: str = "",
        top_k: int = 5,
        selected_text: Optional[str] = None,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[RetrievalResult], RetrievalTelemetry]:
        start_total = time.perf_counter()

        # Resolve document scope
        target_doc_ids = document_ids if document_ids else ([document_id] if document_id else [])
        if not target_doc_ids:
            telemetry = RetrievalTelemetry(
                pipeline_version=settings.RETRIEVAL_PIPELINE_VERSION,
                query=query,
                query_type="empty_scope",
                document_id="none",
                dense_candidate_count=0,
                lexical_candidate_count=0,
                fused_candidate_count=0,
                reranked_count=0,
                final_count=0,
                reranking_enabled=False,
                reranking_skipped=True,
                embedding_provider=settings.EMBEDDING_PROVIDER,
                embedding_model=settings.EMBEDDING_MODEL,
                embedding_dimension=settings.EMBEDDING_DIMENSION,
                dense_latency_ms=0.0,
                lexical_latency_ms=0.0,
                fusion_latency_ms=0.0,
                rerank_latency_ms=0.0,
                total_retrieval_latency_ms=0.0,
            )
            return [], telemetry

        # 1. Query Normalization & Classification
        clean_query, tech_tokens = self.lexical_retriever.normalize_query(query or "")
        effective_query = clean_query if clean_query else (selected_text or "")
        query_type = self.classify_query(query, selected_text)

        # 2. Dynamic Candidate Allocation per Query Type
        dense_k = settings.DENSE_TOP_K
        lexical_k = settings.LEXICAL_TOP_K
        if query_type == "technical_identifier":
            lexical_k = min(25, settings.LEXICAL_TOP_K * 2)
        elif query_type == "conceptual":
            dense_k = min(25, settings.DENSE_TOP_K * 2)

        # 3. Document-Balanced Candidate Retrieval across Target Documents
        t_dense_start = time.perf_counter()
        t_lex_start = time.perf_counter()

        if len(target_doc_ids) > 1:
            # Multi-document mode: Top-K per document allocation to guarantee document balance
            per_doc_dense_k = max(3, dense_k // len(target_doc_ids))
            per_doc_lexical_k = max(3, lexical_k // len(target_doc_ids))

            dense_tasks = [
                self.dense_retriever.retrieve(doc_id, query, top_k=per_doc_dense_k, selected_text=selected_text)
                for doc_id in target_doc_ids
            ]
            lexical_tasks = [
                self.lexical_retriever.retrieve(doc_id, query, top_k=per_doc_lexical_k, selected_text=selected_text)
                for doc_id in target_doc_ids
            ]

            dense_results_per_doc = await asyncio.gather(*dense_tasks)
            lexical_results_per_doc = await asyncio.gather(*lexical_tasks)

            dense_candidates = [c for doc_res in dense_results_per_doc for c in doc_res]
            lexical_candidates = [c for doc_res in lexical_results_per_doc for c in doc_res]
        else:
            single_doc_id = target_doc_ids[0]
            dense_task = asyncio.create_task(
                self.dense_retriever.retrieve(single_doc_id, query, top_k=dense_k, selected_text=selected_text)
            )
            lexical_task = asyncio.create_task(
                self.lexical_retriever.retrieve(single_doc_id, query, top_k=lexical_k, selected_text=selected_text)
            )
            dense_candidates, lexical_candidates = await asyncio.gather(dense_task, lexical_task)

        # Controlled Query Expansion for conceptual queries (if enabled)
        if getattr(settings, "ENABLE_QUERY_EXPANSION", False) and query_type == "conceptual" and clean_query:
            expanded_variant = f"{clean_query} technical details background"
            expanded_dense = await self.dense_retriever.retrieve(
                document_ids=target_doc_ids, query=expanded_variant, top_k=5, selected_text=selected_text
            )
            existing_cids = {c.chunk_id for c in dense_candidates}
            for exp_c in expanded_dense:
                if exp_c.chunk_id not in existing_cids:
                    dense_candidates.append(exp_c)
                    existing_cids.add(exp_c.chunk_id)

        dense_latency = (time.perf_counter() - t_dense_start) * 1000.0
        lexical_latency = (time.perf_counter() - t_lex_start) * 1000.0

        # 4. Candidate Fusion (RRF) & Deduplication
        t_fusion_start = time.perf_counter()
        if settings.ENABLE_HYBRID_RETRIEVAL:
            fused_candidates = self.fusion_service.fuse_and_deduplicate(dense_candidates, lexical_candidates)
        else:
            fused_candidates = dense_candidates
        fusion_latency = (time.perf_counter() - t_fusion_start) * 1000.0

        # 5. Reranking Execution & Safe Degradation Tracking
        t_rerank_start = time.perf_counter()
        rerank_k = settings.RERANK_TOP_K
        candidates_to_rerank = fused_candidates[:rerank_k]

        reranking_enabled = bool(settings.ENABLE_RERANKING and settings.RERANKER_PROVIDER != "disabled")
        reranking_skipped = False

        if reranking_enabled and candidates_to_rerank:
            try:
                final_evidence = await self.reranker.rerank(
                    query=effective_query,
                    candidates=candidates_to_rerank,
                    top_k=top_k
                )
            except Exception as exc:
                logger.warning(f"Reranker failed ({exc}). Gracefully degrading to RRF fused ranking.")
                reranking_skipped = True
                final_evidence = candidates_to_rerank[:top_k]
        else:
            reranking_skipped = True
            final_evidence = candidates_to_rerank[:top_k]

        rerank_latency = (time.perf_counter() - t_rerank_start) * 1000.0

        # 6. Relevance Threshold Filtering (if configured)
        if settings.RETRIEVAL_MIN_SCORE_THRESHOLD > 0.0:
            final_evidence = [
                item for item in final_evidence
                if (item.rerank_score or item.fused_score or item.dense_score or 0.0) >= settings.RETRIEVAL_MIN_SCORE_THRESHOLD
            ]

        total_latency = (time.perf_counter() - start_total) * 1000.0

        primary_doc_id = str(target_doc_ids[0]) if len(target_doc_ids) == 1 else f"multi_{len(target_doc_ids)}"
        telemetry = RetrievalTelemetry(
            pipeline_version=settings.RETRIEVAL_PIPELINE_VERSION,
            query=effective_query,
            query_type=query_type,
            document_id=primary_doc_id,
            dense_candidate_count=len(dense_candidates),
            lexical_candidate_count=len(lexical_candidates),
            fused_candidate_count=len(fused_candidates),
            reranked_count=len(candidates_to_rerank),
            final_count=len(final_evidence),
            reranking_enabled=reranking_enabled,
            reranking_skipped=reranking_skipped,
            embedding_provider=settings.EMBEDDING_PROVIDER,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
            dense_latency_ms=round(dense_latency, 2),
            lexical_latency_ms=round(lexical_latency, 2),
            fusion_latency_ms=round(fusion_latency, 2),
            rerank_latency_ms=round(rerank_latency, 2),
            total_retrieval_latency_ms=round(total_latency, 2),
        )

        logger.info(
            f"[Phase 12 Telemetry] docs={primary_doc_id} query_type='{query_type}' query='{effective_query[:30]}' "
            f"dense={len(dense_candidates)} lex={len(lexical_candidates)} fused={len(fused_candidates)} "
            f"final={len(final_evidence)} rerank_skipped={reranking_skipped} total_time={total_latency:.1f}ms"
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
