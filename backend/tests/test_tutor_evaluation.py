import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_tutor_answer_evaluation_and_hints(client: AsyncClient, user_a_headers: dict):
    # Upload doc & create session
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("eval_doc.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    create_res = await client.post("/api/v1/tutor/sessions", headers=user_a_headers, json={"document_id": doc_id, "title": "Eval & Hints Test"})
    session_id = create_res.json()["id"]

    # Start session & answer diagnostic to get to QUESTION state
    await client.post(f"/api/v1/tutor/sessions/{session_id}/turn", headers=user_a_headers, json={"action": "START"})
    await client.post(f"/api/v1/tutor/sessions/{session_id}/turn", headers=user_a_headers, json={"action": "ANSWER", "user_answer": "I have basic knowledge."})

    # Request Hint 1
    hint_res1 = await client.post(f"/api/v1/tutor/sessions/{session_id}/hint", headers=user_a_headers)
    assert hint_res1.status_code == 200
    h1 = hint_res1.json()
    assert h1["hint_level"] == 1
    assert "hint_text" in h1

    # Request Hint 2
    hint_res2 = await client.post(f"/api/v1/tutor/sessions/{session_id}/hint", headers=user_a_headers)
    assert hint_res2.status_code == 200
    h2 = hint_res2.json()
    assert h2["hint_level"] == 2

    # Submit answer & get evaluation feedback
    ans_res = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "ANSWER", "user_answer": "Detailed answer explaining the concept and its operational boundaries."}
    )
    assert ans_res.status_code == 200
    s_data = ans_res.json()
    assert s_data["status"] == "FEEDBACK"
    history = s_data["history"]
    latest_turn = history[-1]
    assert "feedback" in latest_turn
    assert "score" in latest_turn
