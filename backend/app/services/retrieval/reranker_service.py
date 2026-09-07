import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx

from app.schemas.retrieval import RetrievalResult
from app.core.config import settings
from app.core.logging import logger


class BaseReranker(ABC):
    """Abstract interface boundary for Rerankers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Rerank candidates based on deep semantic query-document alignment."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check reranker service status."""
        pass


class MockReranker(BaseReranker):
    """
    Deterministic zero-dependency Mock Reranker for local testing & CI.
    Evaluates candidate text against query terms, technical tokens, and context alignment.
    """

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        if not candidates:
            return []

        query_terms = [t.lower() for t in re.findall(r'\w+', query) if len(t) >= 2]
        reranked_list: List[RetrievalResult] = []

        for idx, item in enumerate(candidates):
            copy_item = item.model_copy()
            content_lower = item.content.lower()
            
            # Base score from RRF fused score
            base_score = item.fused_score or (1.0 / (60.0 + idx + 1))
            
            # Match query phrase boost
            phrase_boost = 0.0
            if query.lower().strip() in content_lower:
                phrase_boost = 0.35

            # Term overlap boost
            overlap_count = sum(1 for term in query_terms if term in content_lower)
            term_boost = (overlap_count / max(1, len(query_terms))) * 0.25

            final_rerank_score = round(base_score + phrase_boost + term_boost, 4)
            copy_item.rerank_score = final_rerank_score
            reranked_list.append(copy_item)

        # Sort descending by rerank_score
        reranked_list.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)

        for rank_idx, res in enumerate(reranked_list[:top_k]):
            res.final_rank = rank_idx + 1

        return reranked_list[:top_k]

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": "mock",
            "status": "healthy"
        }


class CohereReranker(BaseReranker):
    """
    Cohere API Reranker slot implementation using httpx.
    Gracefully falls back to RRF fused order if Cohere service is unavailable or key is missing.
    """

    def __init__(self, api_key: str = None, model: str = "rerank-english-v3.0"):
        self.api_key = api_key or settings.COHERE_API_KEY
        self.model = model

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        if not candidates:
            return []

        if not self.api_key:
            logger.warning("COHERE_API_KEY missing. Gracefully falling back to RRF fused candidate order.")
            return candidates[:top_k]

        documents = [c.content for c in candidates]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.cohere.com/v2/rerank",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": documents,
                        "top_n": top_k
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Cohere rerank error HTTP {response.status_code}: {response.text}. Falling back to fused order.")
                    return candidates[:top_k]

                data = response.json()
                results = data.get("results", [])

                reranked_output: List[RetrievalResult] = []
                for res_item in results:
                    orig_idx = res_item["index"]
                    score = res_item["relevance_score"]

                    matched_candidate = candidates[orig_idx].model_copy()
                    matched_candidate.rerank_score = round(float(score), 4)
                    reranked_output.append(matched_candidate)

                for rank_idx, res in enumerate(reranked_output):
                    res.final_rank = rank_idx + 1

                return reranked_output
        except Exception as exc:
            logger.error(f"Cohere reranker connection failed ({exc}). Gracefully degrading to RRF fused candidate order.")
            return candidates[:top_k]

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": bool(self.api_key),
            "provider": "cohere",
            "model": self.model,
            "status": "healthy" if self.api_key else "missing_api_key"
        }


class DisabledReranker(BaseReranker):
    """
    Pass-through Reranker implementation when reranking is disabled.
    Preserves input RRF candidate ranking without additional score calculation.
    """

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        return candidates[:top_k]

    async def health_check(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": "disabled",
            "status": "healthy"
        }


def get_reranker() -> BaseReranker:
    """Factory function to get configured reranker provider."""
    provider = settings.RERANKER_PROVIDER.lower()
    if provider == "cohere":
        return CohereReranker(api_key=settings.COHERE_API_KEY)
    elif provider == "disabled":
        return DisabledReranker()
    return MockReranker()
