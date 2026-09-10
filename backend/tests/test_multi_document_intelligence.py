import pytest
import uuid
import fitz  # PyMuPDF
from sqlalchemy import select

from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentChunk
from app.models.workspace import Workspace, WorkspaceDocument
from app.core.security import get_password_hash
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.services.multi_doc_service import MultiDocService
from app.services.agent.tools import get_agent_tools
from tests.fixtures.gold_multidoc_dataset import GOLD_MULTIDOC_DATASET


def create_sample_pdf(title: str, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), f"{title}\n\n{text}", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# 1. Workspace CRUD & Persistence Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workspace_crud_and_persistence(db_session):
    user = User(
        id=uuid.uuid4(),
        email="ws_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Workspace User"
    )
    db_session.add(user)
    await db_session.commit()

    # Create Workspace
    ws = Workspace(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Cybersecurity Research Workspace",
        description="Collection of security whitepapers"
    )
    db_session.add(ws)
    await db_session.commit()

    # Query Workspace
    res = await db_session.execute(select(Workspace).where(Workspace.id == ws.id))
    fetched_ws = res.scalars().first()
    assert fetched_ws is not None
    assert fetched_ws.title == "Cybersecurity Research Workspace"

    # Delete Workspace (Verify underlying documents remain)
    await db_session.delete(fetched_ws)
    await db_session.commit()

    res2 = await db_session.execute(select(Workspace).where(Workspace.id == ws.id))
    assert res2.scalars().first() is None


# ---------------------------------------------------------------------------
# 2. Workspace Ownership & Multi-Tenant Security Isolation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workspace_ownership_security_isolation(client, user_a_headers, user_b_headers):
    pdf_bytes = create_sample_pdf("User A Document", "Sensitive Security Architecture details.")

    # User A uploads a document
    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("usera_doc.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers
    )
    assert res_upload.status_code == 201
    doc_id_a = res_upload.json()["id"]

    # User B creates a workspace
    res_ws_b = await client.post(
        "/api/v1/workspaces",
        json={"title": "User B Workspace", "description": "Private collection"},
        headers=user_b_headers
    )
    assert res_ws_b.status_code == 201
    ws_id_b = res_ws_b.json()["id"]

    # User B attempts to attach User A's document to User B's workspace -> MUST fail (403 Forbidden)
    res_attach = await client.post(
        f"/api/v1/workspaces/{ws_id_b}/documents",
        json={"document_id": doc_id_a},
        headers=user_b_headers
    )
    assert res_attach.status_code == 403

    # User B attempts to query User A's document via workspace query -> MUST fail
    res_query = await client.post(
        f"/api/v1/workspaces/{ws_id_b}/query",
        json={"query": "What is the security architecture?", "selected_document_ids": [doc_id_a]},
        headers=user_b_headers
    )
    assert res_query.status_code == 400


# ---------------------------------------------------------------------------
# 3. Document-Balanced Multi-Document Hybrid Retrieval
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_balanced_hybrid_retrieval(db_session):
    user = User(
        id=uuid.uuid4(),
        email="retrieval_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Retrieval User"
    )
    db_session.add(user)

    doc_a = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Paper A",
        original_filename="paper_a.pdf",
        storage_key="key_a",
        processing_status=DocumentStatus.COMPLETED,
        page_count=2
    )
    doc_b = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Paper B",
        original_filename="paper_b.pdf",
        storage_key="key_b",
        processing_status=DocumentStatus.COMPLETED,
        page_count=2
    )
    db_session.add_all([doc_a, doc_b])

    # Insert sample chunks for Paper A and Paper B
    c_a = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_a.id,
        content="Paper A discusses AES-256 encryption standards and multi-factor authentication (MFA).",
        token_count=15,
        page_start=1,
        page_end=1,
        embedding=[0.1] * 768
    )
    c_b = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_b.id,
        content="Paper B discusses ChaCha20 encryption and OAuth 2.0 authentication frameworks.",
        token_count=15,
        page_start=2,
        page_end=2,
        embedding=[0.1] * 768
    )
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    pipeline = HybridRetrievalPipeline(db_session)
    results, telemetry = await pipeline.execute_pipeline(
        document_ids=[doc_a.id, doc_b.id],
        query="encryption and authentication",
        top_k=4
    )

    assert len(results) >= 2
    retrieved_doc_ids = {r.document_id for r in results}
    assert str(doc_a.id) in retrieved_doc_ids
    assert str(doc_b.id) in retrieved_doc_ids


# ---------------------------------------------------------------------------
# 4. Multi-Document Comparison, Agreement & Contradiction Engines
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_doc_service_comparison_agreement_contradiction(db_session):
    user = User(
        id=uuid.uuid4(),
        email="multidoc_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="MultiDoc User"
    )
    db_session.add(user)

    doc_a = Document(id=uuid.uuid4(), user_id=user.id, title="Paper A.pdf", original_filename="a.pdf", storage_key="ka", processing_status=DocumentStatus.COMPLETED)
    doc_b = Document(id=uuid.uuid4(), user_id=user.id, title="Paper B.pdf", original_filename="b.pdf", storage_key="kb", processing_status=DocumentStatus.COMPLETED)
    db_session.add_all([doc_a, doc_b])

    c_a = DocumentChunk(id=uuid.uuid4(), document_id=doc_a.id, content="Layered defense reduces attack surface significantly. Benchmark throughput is 10Gbps on 10GbE network.", page_start=1, page_end=1, embedding=[0.2]*768)
    c_b = DocumentChunk(id=uuid.uuid4(), document_id=doc_b.id, content="Layered security controls reduce intrusion risks. Benchmark throughput is 1Gbps on 1GbE cloud environment.", page_start=2, page_end=2, embedding=[0.2]*768)
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    service = MultiDocService(db_session)

    # Comparison
    comp_res = await service.compare_documents(user=user, selected_document_ids=[doc_a.id, doc_b.id], topic="Network throughput")
    assert "similarities" in comp_res
    assert len(comp_res["documents"]) == 2

    # Agreement Detection
    agree_res = await service.find_common_claims(user=user, selected_document_ids=[doc_a.id, doc_b.id], topic="Defense in depth")
    assert "agreed_claims" in agree_res

    # Contradiction Detection
    conflict_res = await service.find_conflicting_claims(user=user, selected_document_ids=[doc_a.id, doc_b.id], topic="Throughput benchmark")
    assert "conflicts" in conflict_res


# ---------------------------------------------------------------------------
# 5. Multi-Document Agent Tools Verification
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_document_agent_tools(db_session):
    user = User(
        id=uuid.uuid4(),
        email="tools_multidoc_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Tools MultiDoc User"
    )
    db_session.add(user)

    doc_a = Document(id=uuid.uuid4(), user_id=user.id, title="Doc A", original_filename="a.pdf", storage_key="ka", processing_status=DocumentStatus.COMPLETED)
    db_session.add(doc_a)
    c_a = DocumentChunk(id=uuid.uuid4(), document_id=doc_a.id, content="OAuth 2.0 security token validation.", page_start=1, page_end=1, embedding=[0.3]*768)
    db_session.add(c_a)
    await db_session.commit()

    tools = get_agent_tools(db_session)

    # 1. search_workspace
    res_search = await tools["search_workspace"].run(user, doc_a.id, {"query": "OAuth", "document_ids": [str(doc_a.id)]})
    assert res_search["evidence_count"] >= 1

    # 2. get_document_evidence
    res_ev = await tools["get_document_evidence"].run(user, doc_a.id, {"target_document_id": str(doc_a.id), "query": "OAuth"})
    assert res_ev["evidence_count"] >= 1


# ---------------------------------------------------------------------------
# 6. Deletion Consistency Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_deletion_consistency(db_session):
    user = User(
        id=uuid.uuid4(),
        email="del_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Del User"
    )
    db_session.add(user)

    doc = Document(id=uuid.uuid4(), user_id=user.id, title="Delete Me", original_filename="d.pdf", storage_key="kd", processing_status=DocumentStatus.COMPLETED)
    ws = Workspace(id=uuid.uuid4(), user_id=user.id, title="Workspace", description="Test")
    db_session.add_all([doc, ws])
    await db_session.commit()

    ws_doc = WorkspaceDocument(workspace_id=ws.id, document_id=doc.id)
    db_session.add(ws_doc)
    await db_session.commit()

    # Delete Document -> WorkspaceDocument relation must be removed cleanly
    await db_session.delete(doc)
    await db_session.commit()

    res = await db_session.execute(
        select(WorkspaceDocument).where(WorkspaceDocument.workspace_id == ws.id)
    )
    assert len(res.scalars().all()) == 0


# ---------------------------------------------------------------------------
# 7. Multi-Document Benchmark Dataset Execution
# ---------------------------------------------------------------------------
def test_gold_multidoc_dataset_structure():
    assert len(GOLD_MULTIDOC_DATASET) == 10
    categories = {item["category"] for item in GOLD_MULTIDOC_DATASET}
    assert "simple_cross_document_lookup" in categories
    assert "comparison" in categories
    assert "agreement" in categories
    assert "contradiction" in categories
    assert "unanswerable_across_selected_documents" in categories
