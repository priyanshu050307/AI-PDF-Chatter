import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_tutor_session_state_machine_flow(client: AsyncClient, user_a_headers: dict):
    # 1. Upload sample PDF
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("tutor_doc.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # 2. Create Study Session (State: CREATED)
    create_res = await client.post(
        "/api/v1/tutor/sessions",
        headers=user_a_headers,
        json={
            "document_id": doc_id,
            "title": "State Machine Test Session",
            "topic_scope": {"type": "ENTIRE_DOCUMENT"},
            "difficulty": "BEGINNER",
            "learning_goal": "UNDERSTAND"
        }
    )
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["id"]
    assert session_data["status"] == "CREATED"
    assert session_data["difficulty"] == "BEGINNER"

    # 3. Start Session -> Transition to ASSESSING
    start_turn = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "START"}
    )
    assert start_turn.status_code == 200
    s_data = start_turn.json()
    assert s_data["status"] == "ASSESSING"
    assert len(s_data["history"]) >= 1

    # 4. Answer Diagnostic -> Transition to QUESTION
    diag_turn = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "ANSWER", "user_answer": "It manages system layout and security boundaries."}
    )
    assert diag_turn.status_code == 200
    s_data2 = diag_turn.json()
    assert s_data2["status"] == "QUESTION"

    # 5. Answer Question -> Transition to FEEDBACK
    ans_turn = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "ANSWER", "user_answer": "The primary advantage is ensuring strict memory isolation and predictability."}
    )
    assert ans_turn.status_code == 200
    s_data3 = ans_turn.json()
    assert s_data3["status"] == "FEEDBACK"
    assert s_data3["progress_pct"] > 0

    # 6. Advance to Next Concept
    next_turn = await client.post(
        f"/api/v1/tutor/sessions/{session_id}/turn",
        headers=user_a_headers,
        json={"action": "NEXT_CONCEPT"}
    )
    assert next_turn.status_code == 200
    s_data4 = next_turn.json()
    assert s_data4["status"] in ["TEACHING", "QUESTION", "COMPLETED"]
