import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_tutor_cross_user_isolation(client: AsyncClient, user_a_headers: dict, user_b_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("user_a_private.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # User A creates a study session
    sess_res = await client.post(
        "/api/v1/tutor/sessions",
        headers=user_a_headers,
        json={"document_id": doc_id, "title": "Private Session"}
    )
    session_id = sess_res.json()["id"]

    # User B attempts to access User A's session -> 404
    b_get = await client.get(f"/api/v1/tutor/sessions/{session_id}", headers=user_b_headers)
    assert b_get.status_code == 404

    # User B attempts to turn User A's session -> 404
    b_turn = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_b_headers,
        json={"action": "ANSWER", "user_answer": "Unauthorized attempt"}
    )
    assert b_turn.status_code == 404

    # User B attempts to delete User A's session -> 404
    b_del = await client.delete(f"/api/v1/tutor/sessions/{session_id}", headers=user_b_headers)
    assert b_del.status_code == 404
