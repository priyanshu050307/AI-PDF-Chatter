import pytest
import uuid
import math
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.fusion_service import FusionService
from app.services.retrieval.reranker_service import MockReranker
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.core.security import get_password_hash


def compute_mrr(retrieved_ids, ground_truth_ids):
    """Reciprocal Rank of the first relevant result."""
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in ground_truth_ids:
            return 1.0 / rank
    return 0.0


def compute_ndcg(retrieved_ids, ground_truth_ids, k=5):
    """Normalized Discounted Cumulative Gain at K."""
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


@pytest.mark.asyncio
async def test_retrieval_quality_benchmark(db_session):
    user = User(
        id=uuid.uuid4(),
        email="benchmark_eval_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Benchmark User"
    )
    db_session.add(user)
    await db_session.commit()

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="system_architecture_and_security.pdf",
        original_filename="system_architecture_and_security.pdf",
        storage_key="/tmp/system_architecture_and_security.pdf",
        file_size_bytes=4096,
        processing_status=DocumentStatus.COMPLETED,
        page_count=10
    )
    db_session.add(doc)
    await db_session.commit()

    # Seed benchmark corpus chunks
    c_cve = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=1,
        page_end=1,
        content="Security Vulnerability Advisory: CVE-2026-1234 details a high severity buffer overflow in the RPC parser.",
        token_count=18,
        embedding=[0.8, 0.1, 0.1] + [0.0] * 381
    )
    c_async = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=2,
        page_end=2,
        content="Asynchronous context switching reduces CPU idle overhead and enables high-concurrency event loops for web backend scale.",
        token_count=20,
        embedding=[0.1, 0.8, 0.1] + [0.0] * 381
    )
    c_crypto = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=3,
        page_end=3,
        content="Cryptographic Standards: AES-256 for symmetric block cipher encryption and SHA-256 for cryptographic digest hashing.",
        token_count=18,
        embedding=[0.1, 0.1, 0.8] + [0.0] * 381
    )
    c_oauth = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=4,
        page_end=4,
        content="Enterprise Security Policy mandates OAuth 2.0 protocol with short-lived bearer access tokens and HTTPS TLS enforcement.",
        token_count=20,
        embedding=[0.4, 0.4, 0.1] + [0.0] * 381
    )
    c_jwt = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=5,
        page_end=5,
        content="Authentication Architecture: JWT token refresh mechanism requires rotating refresh tokens stored in secure HttpOnly cookies.",
        token_count=22,
        embedding=[0.3, 0.3, 0.3] + [0.0] * 381
    )
    c_unrelated = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=6,
        page_end=6,
        content="General corporate office guidelines on cafeteria catering and parking permits.",
        token_count=12,
        embedding=[0.0] * 384
    )

    chunks = [c_cve, c_async, c_crypto, c_oauth, c_jwt, c_unrelated]
    db_session.add_all(chunks)
    await db_session.commit()

    # Benchmark test queries and ground truth mappings
    benchmark_queries = [
        {
            "category": "Exact Lookup",
            "query": "What is CVE-2026-1234 vulnerability details?",
            "ground_truth": [c_cve.id]
        },
        {
            "category": "Conceptual Query",
            "query": "How does asynchronous context switching improve throughput?",
            "ground_truth": [c_async.id]
        },
        {
            "category": "Technical Spec",
            "query": "AES-256 and SHA-256 cryptographic standards",
            "ground_truth": [c_crypto.id]
        },
        {
            "category": "Cross-Paragraph",
            "query": "Security policy regarding OAuth 2.0 tokens",
            "ground_truth": [c_oauth.id]
        },
        {
            "category": "Contextual Highlight",
            "query": "Clarify JWT token refresh mechanism",
            "ground_truth": [c_jwt.id]
        },
        {
            "category": "Unanswerable",
            "query": "Quantum hyperdrive engine specifications",
            "ground_truth": []
        }
    ]

    pipeline = HybridRetrievalPipeline(db_session)

    total_recalls = []
    total_precisions = []
    total_mrrs = []
    total_ndcgs = []

    for test_item in benchmark_queries:
        q = test_item["query"]
        gt = test_item["ground_truth"]

        # Run pipeline
        res, telemetry = await pipeline.execute_pipeline(doc.id, q, top_k=3)
        retrieved_ids = [uuid.UUID(r.chunk_id) for r in res]

        if gt:
            hits = [cid for cid in retrieved_ids if cid in gt]
            recall = len(hits) / len(gt)
            precision = len(hits) / len(retrieved_ids) if retrieved_ids else 0.0
            mrr = compute_mrr(retrieved_ids, gt)
            ndcg = compute_ndcg(retrieved_ids, gt, k=3)
        else:
            # Unanswerable query
            recall = 1.0 if len(retrieved_ids) == 0 else 0.0
            precision = 1.0 if len(retrieved_ids) == 0 else 0.0
            mrr = 1.0 if len(retrieved_ids) == 0 else 0.0
            ndcg = 1.0 if len(retrieved_ids) == 0 else 0.0

        total_recalls.append(recall)
        total_precisions.append(precision)
        total_mrrs.append(mrr)
        total_ndcgs.append(ndcg)

    mean_recall = sum(total_recalls) / len(total_recalls)
    mean_mrr = sum(total_mrrs) / len(total_mrrs)
    mean_ndcg = sum(total_ndcgs) / len(total_ndcgs)

    # Benchmark Quality Checks
    assert mean_recall >= 0.8, f"Mean Recall@K expected >= 0.8, got {mean_recall}"
    assert mean_mrr >= 0.8, f"Mean MRR expected >= 0.8, got {mean_mrr}"
    assert mean_ndcg >= 0.8, f"Mean NDCG@K expected >= 0.8, got {mean_ndcg}"
