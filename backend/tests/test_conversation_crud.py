import uuid
import pytest
from httpx import AsyncClient
from app.models.document import Document, DocumentStatus


@pytest.mark.asyncio
async def test_conversation_crud_and_security(client: AsyncClient, user_a_headers: dict, user_b_headers: dict, db_session):
    # Fetch User A profile
    res_a = await client.get("/api/v1/users/me", headers=user_a_headers)
    user_a_id = uuid.UUID(res_a.json()["id"])

    # Create Document for User A
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a_id,
        title="CRUD Test Doc",
        original_filename="crud.pdf",
        storage_key="k_crud",
        file_size_bytes=1024,
        page_count=5,
        processing_status=DocumentStatus.COMPLETED
    )
    db_session.add(doc)
    await db_session.flush()

    # 1. Create Conversation
    res_create = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Initial Title"}
    )
    assert res_create.status_code == 201
    conv_data = res_create.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Initial Title"

    # 2. List Conversations for Document
    res_list = await client.get(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Rename Conversation (PATCH)
    res_rename = await client.patch(
        f"/api/v1/conversations/{conv_id}",
        headers=user_a_headers,
        json={"title": "Renamed Title"}
    )
    assert res_rename.status_code == 200
    assert res_rename.json()["title"] == "Renamed Title"

    # 4. Security Check: User B tries to rename User A's conversation -> 404
    res_b_rename = await client.patch(
        f"/api/v1/conversations/{conv_id}",
        headers=user_b_headers,
        json={"title": "Hacked Title"}
    )
    assert res_b_rename.status_code == 404

    # 5. Send messages to test pagination
    for i in range(5):
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=user_a_headers,
            json={"content": f"Test question {i+1}"}
        )

    # 6. Get Paginated Messages
    res_msgs = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?limit=4",
        headers=user_a_headers
    )
    assert res_msgs.status_code == 200
    page_data = res_msgs.json()
    assert page_data["total"] >= 10  # 5 user questions + 5 assistant answers
    assert len(page_data["items"]) == 4

    # 7. Delete Conversation (DELETE)
    res_del = await client.delete(
        f"/api/v1/conversations/{conv_id}",
        headers=user_a_headers
    )
    assert res_del.status_code == 204

    # Verify conversation is gone
    res_get_deleted = await client.get(
        f"/api/v1/conversations/{conv_id}",
        headers=user_a_headers
    )
    assert res_get_deleted.status_code == 404
