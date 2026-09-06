import uuid
import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentChunk
from app.services.embedding_service import MockEmbeddingService


@pytest.mark.asyncio
async def test_conversation_create_list_and_chat_api(client: AsyncClient, user_a_headers: dict, db_session):
    # 1. Fetch current User A profile
    profile_res = await client.get("/api/v1/users/me", headers=user_a_headers)
    assert profile_res.status_code == 200
    user_a_id = uuid.UUID(profile_res.json()["id"])

    # 2. Setup completed document and chunk in db_session
    doc_id = uuid.uuid4()
    chunk_text = "The AI PDF Chatter architecture supports multi-tenant context-aware RAG search."
    
    embedder = MockEmbeddingService(dimension=1536)
    vecs = await embedder.generate_embeddings([chunk_text])

    doc = Document(
        id=doc_id,
        user_id=user_a_id,
        title="API Chat Test Document",
        original_filename="api_test.pdf",
        storage_key="test_storage_key",
        file_size_bytes=1024,
        page_count=5,
        processing_status=DocumentStatus.COMPLETED
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_start=1,
        page_end=2,
        chapter_title="Architecture",
        section_title="RAG Search",
        content=chunk_text,
        token_count=25,
        embedding=vecs[0]
    )
    db_session.add_all([doc, chunk])
    await db_session.flush()

    # 3. Create conversation via API
    res_create = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Test API Conversation"}
    )
    assert res_create.status_code == 201
    conv_data = res_create.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Test API Conversation"

    # 4. List conversations via API
    res_list = await client.get(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 5. Send message via API
    res_msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={"content": chunk_text}
    )
    assert res_msg.status_code == 200
    msg_data = res_msg.json()
    assert msg_data["sender"] == "assistant"
    assert msg_data["content"] is not None
    assert len(msg_data["citations"]) >= 1


@pytest.mark.asyncio
async def test_cross_user_conversation_isolation(client: AsyncClient, user_a_headers: dict, user_b_headers: dict, db_session):
    # Fetch User B ID
    profile_res = await client.get("/api/v1/users/me", headers=user_b_headers)
    assert profile_res.status_code == 200
    user_b_id = uuid.UUID(profile_res.json()["id"])

    # Document owned by User B
    doc_id = uuid.uuid4()
    doc_b = Document(
        id=doc_id,
        user_id=user_b_id,
        title="User B Private Doc",
        original_filename="user_b.pdf",
        storage_key="k_b",
        file_size_bytes=500,
        page_count=2,
        processing_status=DocumentStatus.COMPLETED
    )
    db_session.add(doc_b)
    await db_session.flush()

    # User A tries to create a conversation on User B's document -> Expect 404
    res_unauth = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Unauthorized Conv"}
    )
    assert res_unauth.status_code == 404
