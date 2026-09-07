import asyncio
import sys
import math
import uuid

sys.path.insert(0, "backend")

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.fusion_service import FusionService
from app.services.retrieval.reranker_service import MockReranker
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.core.security import get_password_hash

def compute_mrr(retrieved_ids, ground_truth_ids):
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in ground_truth_ids:
            return 1.0 / rank
    return 0.0

def compute_ndcg(retrieved_ids, ground_truth_ids, k=5):
    dcg = 0.0
    for rank, cid in enumerate(retrieved_ids[:k], start=1):
        rel = 1.0 if cid in ground_truth_ids else 0.0
        dcg += rel / math.log2(rank + 1)
    idcg = 0.0
    for rank in range(1, min(len(ground_truth_ids), k) + 1):
        idcg += 1.0 / math.log2(rank + 1)
    if idcg == 0.0:
        return 1.0 if len(ground_truth_ids) == 0 else 0.0
    return dcg / idcg

async def run_comparative_benchmark():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"benchmark_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=get_password_hash("Password123!"),
            full_name="Benchmark User"
        )
        session.add(user)
        await session.commit()

        doc = Document(
            id=uuid.uuid4(),
            user_id=user.id,
            title="system_security_spec.pdf",
            original_filename="system_security_spec.pdf",
            storage_key="/tmp/system_security_spec.pdf",
            file_size_bytes=4096,
            processing_status=DocumentStatus.COMPLETED,
            page_count=10
        )
        session.add(doc)
        await session.commit()

        c_cve = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=1,
            page_end=1,
            content="Critical Security Advisory: CVE-2026-1234 details a high severity buffer overflow vulnerability in the RPC parser module.",
            token_count=20,
            embedding=[0.8, 0.1, 0.1] + [0.0] * 765
        )
        c_async = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=2,
            page_end=2,
            content="Asynchronous context switching reduces CPU idle overhead and enables high-concurrency event loops for web backend scale.",
            token_count=20,
            embedding=[0.1, 0.8, 0.1] + [0.0] * 765
        )
        c_crypto = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=3,
            page_end=3,
            content="Cryptographic Standards: AES-256 for symmetric block cipher encryption and SHA-256 for cryptographic digest hashing.",
            token_count=18,
            embedding=[0.1, 0.1, 0.8] + [0.0] * 765
        )
        c_oauth = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=4,
            page_end=4,
            content="Enterprise Security Policy mandates OAuth 2.0 protocol with short-lived bearer access tokens and HTTPS TLS enforcement.",
            token_count=20,
            embedding=[0.4, 0.4, 0.1] + [0.0] * 765
        )
        c_jwt = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=5,
            page_end=5,
            content="Authentication Architecture: JWT token refresh mechanism requires rotating refresh tokens stored in secure HttpOnly cookies.",
            token_count=22,
            embedding=[0.3, 0.3, 0.3] + [0.0] * 765
        )
        c_unrelated = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            page_start=6,
            page_end=6,
            content="General corporate office guidelines on cafeteria catering and parking permits.",
            token_count=12,
            embedding=[0.0] * 768
        )

        session.add_all([c_cve, c_async, c_crypto, c_oauth, c_jwt, c_unrelated])
        await session.commit()

        benchmark_queries = [
            {"query": "What is CVE-2026-1234 vulnerability details?", "gt": [c_cve.id]},
            {"query": "Why does asynchronous context switching improve throughput?", "gt": [c_async.id]},
            {"query": "AES-256 and SHA-256 cryptographic standards", "gt": [c_crypto.id]},
            {"query": "Security policy regarding OAuth 2.0 tokens", "gt": [c_oauth.id]},
            {"query": "Clarify JWT token refresh mechanism", "gt": [c_jwt.id]},
            {"query": "Unanswerable quantum engine specs", "gt": []}
        ]

        dense_retriever = DenseRetriever(session)
        lexical_retriever = LexicalRetriever(session)
        fusion_service = FusionService()
        mock_reranker = MockReranker()

        # Evaluate 3 Pipeline Variants
        variants = ["Baseline Dense", "Version 2 Hybrid (Dense+Lexical)", "Version 3 Hybrid + Reranker"]
        metrics = {v: {"recall": [], "precision": [], "mrr": [], "ndcg": []} for v in variants}

        for item in benchmark_queries:
            q = item["query"]
            gt = item["gt"]

            # Variant 1: Baseline Dense
            dense_res = await dense_retriever.retrieve(doc.id, q, top_k=3)
            dense_ids = [uuid.UUID(r.chunk_id) for r in dense_res]

            # Variant 2: Hybrid
            lex_res = await lexical_retriever.retrieve(doc.id, q, top_k=3)
            fused_res = fusion_service.fuse_and_deduplicate(dense_res, lex_res)[:3]
            fused_ids = [uuid.UUID(r.chunk_id) for r in fused_res]

            # Variant 3: Hybrid + Reranker
            reranked_res = await mock_reranker.rerank(q, fused_res, top_k=3)
            reranked_ids = [uuid.UUID(r.chunk_id) for r in reranked_res]

            for v_name, res_ids in [("Baseline Dense", dense_ids), ("Version 2 Hybrid (Dense+Lexical)", fused_ids), ("Version 3 Hybrid + Reranker", reranked_ids)]:
                if gt:
                    hits = [cid for cid in res_ids if cid in gt]
                    rec = len(hits) / len(gt)
                    prec = len(hits) / len(res_ids) if res_ids else 0.0
                    mrr_v = compute_mrr(res_ids, gt)
                    ndcg_v = compute_ndcg(res_ids, gt, k=3)
                else:
                    rec = 1.0 if len(res_ids) == 0 else 0.0
                    prec = 1.0 if len(res_ids) == 0 else 0.0
                    mrr_v = 1.0 if len(res_ids) == 0 else 0.0
                    ndcg_v = 1.0 if len(res_ids) == 0 else 0.0

                metrics[v_name]["recall"].append(rec)
                metrics[v_name]["precision"].append(prec)
                metrics[v_name]["mrr"].append(mrr_v)
                metrics[v_name]["ndcg"].append(ndcg_v)

        print("\n=======================================================")
        print(" PHASE 8 ADVANCED RETRIEVAL EVALUATION BENCHMARK TABLE ")
        print("=======================================================")
        print(f"{'Pipeline Variant':<35} | {'Recall@3':<10} | {'Precision@3':<12} | {'MRR':<8} | {'NDCG@3':<8}")
        print("-" * 82)

        for v_name in variants:
            m = metrics[v_name]
            mean_rec = sum(m["recall"]) / len(m["recall"])
            mean_prec = sum(m["precision"]) / len(m["precision"])
            mean_mrr = sum(m["mrr"]) / len(m["mrr"])
            mean_ndcg = sum(m["ndcg"]) / len(m["ndcg"])
            print(f"{v_name:<35} | {mean_rec:<10.4f} | {mean_prec:<12.4f} | {mean_mrr:<8.4f} | {mean_ndcg:<8.4f}")

        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_comparative_benchmark())
