import uuid
import pytest
from httpx import AsyncClient
from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.services.embedding_service import MockEmbeddingService


@pytest.mark.asyncio
async def test_context_snapshot_history_immutability(client: AsyncClient, user_a_headers: dict, db_session):
    res_a = await client.get("/api/v1/users/me", headers=user_a_headers)
    user_a_id = uuid.UUID(res_a.json()["id"])

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a_id,
        title="Immutability Test Doc",
        original_filename="immutability.pdf",
        storage_key="k_imm",
        file_size_bytes=1024,
        page_count=100,
        processing_status=DocumentStatus.COMPLETED
    )

    page10 = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=10,
        raw_text="Page 10 content discussing symmetric cryptography.",
        page_width=612.0,
        page_height=792.0
    )

    page25 = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=25,
        raw_text="Page 25 content discussing public key infrastructure.",
        page_width=612.0,
        page_height=792.0
    )

    embedder = MockEmbeddingService(dimension=1536)
    vecs = await embedder.generate_embeddings([page10.raw_text, page25.raw_text])

    chunk10 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_start=10,
        page_end=10,
        content=page10.raw_text,
        token_count=10,
        embedding=vecs[0]
    )

    chunk25 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_start=25,
        page_end=25,
        content=page25.raw_text,
        token_count=10,
        embedding=vecs[1]
    )

    db_session.add_all([doc, page10, page25, chunk10, chunk25])
    await db_session.flush()

    # 1. Create Conversation
    res_conv = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Snapshot Immutability Test"}
    )
    assert res_conv.status_code == 201
    conv_id = res_conv.json()["id"]

    # 2. Send Message 1 on Page 10 with Selection A
    res_msg1 = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "Explain symmetric cryptography",
            "context_snapshot": {
                "document_id": str(doc_id),
                "page_number": 10,
                "selection": {"selected_text": "symmetric cryptography", "page_number": 10}
            }
        }
    )
    assert res_msg1.status_code == 200

    # 3. Send Message 2 on Page 25 with Selection B
    res_msg2 = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "Explain public key infrastructure",
            "context_snapshot": {
                "document_id": str(doc_id),
                "page_number": 25,
                "selection": {"selected_text": "public key infrastructure", "page_number": 25}
            }
        }
    )
    assert res_msg2.status_code == 200

    # 4. Reopen Conversation and verify historical snapshots remain immutable
    res_get = await client.get(
        f"/api/v1/conversations/{conv_id}",
        headers=user_a_headers
    )
    assert res_get.status_code == 200
    msgs = res_get.json()["messages"]

    # Find assistant responses
    assistant_msgs = [m for m in msgs if m["sender"] == "assistant"]
    assert len(assistant_msgs) == 2

    # Verify Message 1 snapshot retained Page 10
    assert assistant_msgs[0]["context_snapshot"]["page_number"] == 10
    assert assistant_msgs[0]["context_snapshot"]["selection_snippet"] == "symmetric cryptography"

    # Verify Message 2 snapshot retained Page 25
    assert assistant_msgs[1]["context_snapshot"]["page_number"] == 25
    assert assistant_msgs[1]["context_snapshot"]["selection_snippet"] == "public key infrastructure"
