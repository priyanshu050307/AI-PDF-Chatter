import uuid
import pytest
from httpx import AsyncClient
from app.models.document import Document, DocumentStatus
from app.models.user import User


@pytest.mark.asyncio
async def test_context_security_document_mismatch(client: AsyncClient, user_a_headers: dict, db_session):
    # Fetch User A profile
    res_a = await client.get("/api/v1/users/me", headers=user_a_headers)
    user_a_id = uuid.UUID(res_a.json()["id"])

    doc_a_id = uuid.uuid4()
    doc_a = Document(
        id=doc_a_id,
        user_id=user_a_id,
        title="Document A",
        original_filename="doc_a.pdf",
        storage_key="k_a",
        file_size_bytes=100,
        page_count=10,
        processing_status=DocumentStatus.COMPLETED
    )
    db_session.add(doc_a)
    await db_session.commit()

    # Create conversation on Document A
    res_conv = await client.post(
        f"/api/v1/documents/{doc_a_id}/conversations",
        headers=user_a_headers,
        json={"title": "Security Test Conv"}
    )
    assert res_conv.status_code == 201
    conv_id = res_conv.json()["id"]

    # Send message supplying a fake/mismatched document_id in context payload
    fake_doc_id = str(uuid.uuid4())
    res_msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "Attempt context injection",
            "context_snapshot": {
                "document_id": fake_doc_id,
                "page_number": 1,
                "selection": {"selected_text": "Fake injection text", "page_number": 1}
            }
        }
    )
    assert res_msg.status_code == 400
    assert "Context document_id does not match" in res_msg.json()["error"]["message"]


@pytest.mark.asyncio
async def test_context_security_invalid_page_number(client: AsyncClient, user_a_headers: dict, db_session):
    res_a = await client.get("/api/v1/users/me", headers=user_a_headers)
    user_a_id = uuid.UUID(res_a.json()["id"])

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=user_a_id,
        title="10 Page Doc",
        original_filename="doc_10.pdf",
        storage_key="k_10",
        file_size_bytes=100,
        page_count=10,
        processing_status=DocumentStatus.COMPLETED
    )
    db_session.add(doc)
    await db_session.commit()

    res_conv = await client.post(
        f"/api/v1/documents/{doc_id}/conversations",
        headers=user_a_headers,
        json={"title": "Page Bounds Test Conv"}
    )
    assert res_conv.status_code == 201
    conv_id = res_conv.json()["id"]

    # Send message with page_number = 999 (exceeds page_count = 10)
    res_msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=user_a_headers,
        json={
            "content": "What is on page 999?",
            "context_snapshot": {
                "document_id": str(doc_id),
                "page_number": 999,
                "selection": {"selected_text": "OutOfBounds text", "page_number": 999}
            }
        }
    )
    assert res_msg.status_code == 400
    assert "Invalid context page_number" in res_msg.json()["error"]["message"]
