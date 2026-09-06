import uuid
import pytest
from httpx import AsyncClient
from app.models.document import Document, DocumentStatus, DocumentChunk, DocumentPage
from app.services.embedding_service import MockEmbeddingService


@pytest.mark.asyncio
async def test_context_aware_chat_actions(client: AsyncClient, user_a_headers: dict, db_session):
    res_a = await client.get("/api/v1/users/me", headers=user_a_headers)
    user_a_id = uuid.UUID(res_a.json()["id"])

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a_id,
        title="Cybersecurity Handbook",
        original_filename="cyber.pdf",
        storage_key="k_cyber",
        file_size_bytes=2048,
        page_count=50,
        processing_status=DocumentStatus.COMPLETED
    )

    page = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=12,
        raw_text="Defense in depth uses multiple independent security controls to protect computing assets.",
        page_width=612.0,
        page_height=792.0
    )

    embedder = MockEmbeddingService(dimension=1536)
    vecs = await embedder.generate_embeddings([page.raw_text])

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_start=12,
        page_end=12,
        chapter_title="Network Security",
        section_title="Defense in Depth",
        content=page.raw_text,
        token_count=15,
        embedding=vecs[0]
    )

    db_session.add_all([doc, page, chunk])
    await db_session.flush()

    # 1. Create Conversation
    res_conv = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Context Chat Test"}
    )
    assert res_conv.status_code == 201
    conv_id = res_conv.json()["id"]

    # 2. Test EXPLAIN Action with Active Selection & Context Snapshot
    selection_text = "Defense in depth uses multiple independent security controls"
    res_explain = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "Explain this.",
            "intent": "EXPLAIN",
            "context_snapshot": {
                "document_id": str(doc_id),
                "page_number": 12,
                "chapter_title": "Network Security",
                "section_title": "Defense in Depth",
                "intent": "EXPLAIN",
                "selection": {
                    "selected_text": selection_text,
                    "page_number": 12
                }
            }
        }
    )

    assert res_explain.status_code == 200
    explain_data = res_explain.json()
    assert explain_data["sender"] == "assistant"
    assert explain_data["context_snapshot"]["has_selection"] is True
    assert explain_data["context_snapshot"]["intent"] == "EXPLAIN"
    assert explain_data["context_snapshot"]["page_number"] == 12
    assert len(explain_data["citations"]) >= 1

    # 3. Test SIMPLIFY Action
    res_simplify = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "Simplify this passage.",
            "intent": "SIMPLIFY",
            "context_snapshot": {
                "document_id": str(doc_id),
                "page_number": 12,
                "intent": "SIMPLIFY",
                "selection": {
                    "selected_text": selection_text,
                    "page_number": 12
                }
            }
        }
    )
    assert res_simplify.status_code == 200
    simplify_data = res_simplify.json()
    assert simplify_data["context_snapshot"]["intent"] == "SIMPLIFY"

    # 4. Test Normal RAG Query after Clearing Context (no selection in snapshot)
    res_normal = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "What security architecture is discussed?",
            "intent": "QUESTION"
        }
    )
    assert res_normal.status_code == 200
    normal_data = res_normal.json()
    assert normal_data["context_snapshot"]["has_selection"] is False
    assert len(normal_data["citations"]) >= 1
