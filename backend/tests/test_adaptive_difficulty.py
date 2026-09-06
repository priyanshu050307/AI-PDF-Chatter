import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_adaptive_difficulty_progression(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("adapt_doc.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    create_res = await client.post("/api/v1/tutor/sessions", headers=user_a_headers, json={"document_id": doc_id, "difficulty": "BEGINNER"})
    session_id = create_res.json()["id"]

    # Start session
    await client.post(f"/api/v1/tutor/sessions/{session_id}/turn", headers=user_a_headers, json={"action": "START"})
    await client.post(f"/api/v1/tutor/sessions/{session_id}/turn", headers=user_a_headers, json={"action": "ANSWER", "user_answer": "I know basic concepts."})

    # Turn 1: High scoring answer
    turn1 = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "ANSWER", "user_answer": "Comprehensive answer demonstrating clear mastery of structure and execution details."}
    )
    assert turn1.status_code == 200

    # Advance to next concept & turn 2: High scoring answer
    await client.post(f"/api/v1/tutor/sessions/{session_id}/turn", headers=user_a_headers, json={"action": "NEXT_CONCEPT"})
    turn2 = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "ANSWER", "user_answer": "Another detailed and highly accurate response covering principles and edge cases."}
    )
    assert turn2.status_code == 200
    s_data = turn2.json()
    assert s_data["difficulty"] in ["INTERMEDIATE", "ADVANCED"]
