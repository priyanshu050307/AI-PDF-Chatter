from typing import List, Dict
from app.schemas.retrieval import RetrievalResult
from app.core.config import settings


class FusionService:
    """
    Reciprocal Rank Fusion (RRF) & Candidate Deduplication Service.
    Combines ranked candidate streams (Dense Vector + Lexical Search) using:
        RRF_score(chunk) = Σ 1.0 / (k + rank)
    where k = settings.RRF_K (default 60.0).
    """

    def __init__(self, rrf_k: float = None):
        self.rrf_k = rrf_k if rrf_k is not None else settings.RRF_K

    def fuse_and_deduplicate(
        self,
        dense_results: List[RetrievalResult],
        lexical_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        fused_map: Dict[str, RetrievalResult] = {}
        scores_map: Dict[str, float] = {}

        # 1. Process Dense Results RRF Ranks
        for rank_idx, item in enumerate(dense_results):
            cid = item.chunk_id
            rank = rank_idx + 1  # 1-indexed rank
            rrf_score = 1.0 / (self.rrf_k + rank)

            if cid not in fused_map:
                fused_map[cid] = item.model_copy()
                scores_map[cid] = 0.0

            fused_map[cid].dense_score = item.dense_score
            scores_map[cid] += rrf_score

        # 2. Process Lexical Results RRF Ranks
        for rank_idx, item in enumerate(lexical_results):
            cid = item.chunk_id
            rank = rank_idx + 1  # 1-indexed rank
            rrf_score = 1.0 / (self.rrf_k + rank)

            if cid not in fused_map:
                fused_map[cid] = item.model_copy()
                scores_map[cid] = 0.0

            fused_map[cid].lexical_score = item.lexical_score
            scores_map[cid] += rrf_score

        # 3. Assign fused RRF scores & sort candidates
        fused_list: List[RetrievalResult] = []
        for cid, res in fused_map.items():
            score = round(scores_map[cid], 6)
            res.fused_score = score
            res.rrf_score = score
            fused_list.append(res)

        fused_list.sort(key=lambda x: x.fused_score or 0.0, reverse=True)

        # 4. Assign initial fused rank positions
        for idx, res in enumerate(fused_list):
            res.final_rank = idx + 1

        return fused_list

    @staticmethod
    def rrf_fusion(
        dense_results: List[RetrievalResult],
        lexical_results: List[RetrievalResult],
        rrf_k: float = 60.0
    ) -> List[RetrievalResult]:
        return FusionService(rrf_k=rrf_k).fuse_and_deduplicate(dense_results, lexical_results)

