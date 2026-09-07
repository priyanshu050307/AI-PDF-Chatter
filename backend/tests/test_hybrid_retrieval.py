import pytest
import uuid
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User
from app.services.retrieval.dense_retriever import DenseRetriever
from app.services.retrieval.lexical_retriever import LexicalRetriever
from app.services.retrieval.fusion_service import FusionService
from app.services.retrieval.reranker_service import BaseReranker, MockReranker, CohereReranker
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.schemas.retrieval import RetrievalResult
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_dense_and_lexical_retrieval(db_session):
    user = User(
        id=uuid.uuid4(),
        email="test_retrieval_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Retrieval User"
    )
    db_session.add(user)
    await db_session.commit()

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="security_report.pdf",
        original_filename="security_report.pdf",
        storage_key="/tmp/security_report.pdf",
        file_size_bytes=1024,
        processing_status=DocumentStatus.COMPLETED,
        page_count=5
    )
    db_session.add(doc)
    await db_session.commit()

    c1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=1,
        page_end=1,
        content="Critical security vulnerability CVE-2026-1234 found in authentication service.",
        token_count=12,
        embedding=[0.1] * 384
    )
    c2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=2,
        page_end=2,
        content="AES-256 encryption standard ensures confidential data storage.",
        token_count=10,
        embedding=[0.05] * 384
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    # Test Dense Retriever
    dense_retriever = DenseRetriever(db_session)
    dense_results = await dense_retriever.retrieve(doc.id, [0.1] * 384, top_k=5)
    assert len(dense_results) == 2
    assert dense_results[0].chunk_id == str(c1.id)

    # Test Lexical Retriever
    lexical_retriever = LexicalRetriever(db_session)
    lexical_results = await lexical_retriever.retrieve(doc.id, "CVE-2026-1234", top_k=5)
    assert len(lexical_results) >= 1
    assert lexical_results[0].chunk_id == str(c1.id)
    assert "CVE-2026-1234" in lexical_results[0].content


@pytest.mark.asyncio
async def test_technical_term_preservation(db_session):
    user = User(
        id=uuid.uuid4(),
        email="tech_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Tech User"
    )
    db_session.add(user)
    await db_session.commit()

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="specs.pdf",
        original_filename="specs.pdf",
        storage_key="/tmp/specs.pdf",
        file_size_bytes=512,
        processing_status=DocumentStatus.COMPLETED,
        page_count=2
    )
    db_session.add(doc)
    await db_session.commit()

    c1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=1,
        page_end=1,
        content="OAuth 2.0 authorization framework uses JWT access tokens signed with SHA-256.",
        token_count=15
    )
    c2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=2,
        page_end=2,
        content="General background information about standard web protocols.",
        token_count=8
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    lexical_retriever = LexicalRetriever(db_session)
    results = await lexical_retriever.retrieve(doc.id, "OAuth 2.0 JWT SHA-256", top_k=5)
    assert len(results) > 0
    assert results[0].chunk_id == str(c1.id)


@pytest.mark.asyncio
async def test_fusion_and_deduplication():
    chunk_id_1 = str(uuid.uuid4())
    chunk_id_2 = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    dense_candidates = [
        RetrievalResult(chunk_id=chunk_id_1, document_id=doc_id, content="Content A", page_start=1, page_end=1, dense_score=0.9),
        RetrievalResult(chunk_id=chunk_id_2, document_id=doc_id, content="Content B", page_start=2, page_end=2, dense_score=0.7),
    ]
    lexical_candidates = [
        RetrievalResult(chunk_id=chunk_id_2, document_id=doc_id, content="Content B", page_start=2, page_end=2, lexical_score=0.95),
        RetrievalResult(chunk_id=chunk_id_1, document_id=doc_id, content="Content A", page_start=1, page_end=1, lexical_score=0.4),
    ]

    fused = FusionService.rrf_fusion(dense_candidates, lexical_candidates, rrf_k=60)
    assert len(fused) == 2
    assert fused[0].rrf_score > 0
    assert fused[0].chunk_id in [chunk_id_1, chunk_id_2]


@pytest.mark.asyncio
async def test_reranker_service():
    chunk_id_1 = str(uuid.uuid4())
    chunk_id_2 = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    candidates = [
        RetrievalResult(chunk_id=chunk_id_1, document_id=doc_id, content="Basic encryption overview", page_start=1, page_end=1, rrf_score=0.03),
        RetrievalResult(chunk_id=chunk_id_2, document_id=doc_id, content="AES-256 key schedule and block size", page_start=2, page_end=2, rrf_score=0.02),
    ]

    mock_reranker = MockReranker()
    reranked = await mock_reranker.rerank("AES-256 key", candidates)
    assert len(reranked) == 2
    assert reranked[0].chunk_id == chunk_id_2
    assert reranked[0].rerank_score > reranked[1].rerank_score

    cohere_reranker = CohereReranker()
    fallback_res = await cohere_reranker.rerank("query", candidates)
    assert len(fallback_res) == len(candidates)


@pytest.mark.asyncio
async def test_pipeline_end_to_end(db_session):
    user = User(
        id=uuid.uuid4(),
        email="pipeline_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Pipeline User"
    )
    db_session.add(user)
    await db_session.commit()

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="pipeline_doc.pdf",
        original_filename="pipeline_doc.pdf",
        storage_key="/tmp/pipeline_doc.pdf",
        file_size_bytes=2048,
        processing_status=DocumentStatus.COMPLETED,
        page_count=3
    )
    db_session.add(doc)
    await db_session.commit()

    c1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=1,
        page_end=1,
        content="JWT token expiration and refresh token rotation policy.",
        token_count=10,
        embedding=[0.2] * 384
    )
    c2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=2,
        page_end=2,
        content="Unrelated section on frontend UI styling and CSS variables.",
        token_count=9,
        embedding=[0.01] * 384
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    pipeline = HybridRetrievalPipeline(db_session)
    results, telemetry = await pipeline.execute_pipeline(
        document_id=doc.id,
        query="refresh token rotation JWT",
        top_k=2
    )

    assert len(results) >= 1
    assert results[0].chunk_id == str(c1.id)
    assert results[0].page_start == 1
    assert telemetry.dense_candidate_count >= 0
    assert telemetry.lexical_candidate_count >= 1
    assert telemetry.total_retrieval_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_debug_endpoint(client, user_a_headers, db_session):
    user_res = await client.get("/api/v1/users/me", headers=user_a_headers)
    assert user_res.status_code == 200
    user_id = uuid.UUID(user_res.json()["id"])

    doc = Document(
        id=uuid.uuid4(),
        user_id=user_id,
        title="debug_doc.pdf",
        original_filename="debug_doc.pdf",
        storage_key="/tmp/debug_doc.pdf",
        file_size_bytes=1024,
        processing_status=DocumentStatus.COMPLETED,
        page_count=1
    )
    db_session.add(doc)
    await db_session.commit()

    c1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        page_start=1,
        page_end=1,
        content="Debug endpoint test chunk content for technical inspection.",
        token_count=10
    )
    db_session.add(c1)
    await db_session.commit()

    debug_res = await client.post(
        f"/api/v1/documents/{doc.id}/retrieval/debug",
        headers=user_a_headers,
        json={"query": "debug endpoint test", "top_k": 3}
    )
    assert debug_res.status_code == 200
    data = debug_res.json()
    assert data["query"] == "debug endpoint test"
    assert "telemetry" in data
    assert "final_evidence" in data


@pytest.mark.asyncio
async def test_query_type_classification(db_session):
    pipeline = HybridRetrievalPipeline(db_session)
    assert pipeline.classify_query("What is CVE-2026-1234 vulnerability?") == "technical_identifier"
    assert pipeline.classify_query("Why is asymmetric encryption slower than symmetric?") == "conceptual"
    assert pipeline.classify_query("Explain OAuth 2.0 PKCE flow") == "technical_identifier"
    assert pipeline.classify_query("General document summary") == "general"
    assert pipeline.classify_query("Explain this", selected_text="Selected paragraph context") == "contextual"
