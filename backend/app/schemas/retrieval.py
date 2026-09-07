import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """Structured evidence model for dense, lexical, fused, and reranked chunks."""
    chunk_id: str
    document_id: str
    content: str
    page_start: int
    page_end: int
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    token_count: int = 0
    dense_score: Optional[float] = None
    lexical_score: Optional[float] = None
    fused_score: Optional[float] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    final_rank: int = 0


class RetrievalTelemetry(BaseModel):
    """Telemetry logging metadata for advanced retrieval operations."""
    pipeline_version: str = "hybrid-v1"
    query: str
    query_type: str = "general"
    document_id: str
    dense_candidate_count: int = 0
    lexical_candidate_count: int = 0
    fused_candidate_count: int = 0
    reranked_count: int = 0
    final_count: int = 0
    reranking_enabled: bool = True
    reranking_skipped: bool = False
    embedding_provider: str = "ollama"
    embedding_model: str = "embeddinggemma"
    embedding_dimension: int = 768
    dense_latency_ms: float = 0.0
    lexical_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    total_retrieval_latency_ms: float = 0.0


class RetrievalDebugRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    selected_text: Optional[str] = None


class RetrievalDebugResponse(BaseModel):
    query: str
    normalized_query: str
    document_id: str
    pipeline_version: str
    dense_candidates: List[RetrievalResult] = Field(default_factory=list)
    lexical_candidates: List[RetrievalResult] = Field(default_factory=list)
    fused_candidates: List[RetrievalResult] = Field(default_factory=list)
    final_evidence: List[RetrievalResult] = Field(default_factory=list)
    telemetry: RetrievalTelemetry
