import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_quiz_generation_and_submission(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("quiz_doc.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # 1. Generate Quiz
    gen_res = await client.post(
        "/api/v1/tutor/quizzes/generate",
        headers=user_a_headers,
        json={"document_id": doc_id, "question_count": 3}
    )
    assert gen_res.status_code == 201
    quiz = gen_res.json()
    quiz_id = quiz["id"]
    questions = quiz["questions"]
    assert len(questions) >= 1
    assert "source_citations" in questions[0]

    # 2. Get Quiz Detail
    get_res = await client.get(f"/api/v1/tutor/quizzes/{quiz_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == quiz_id

    # 3. Submit Quiz Answers
    user_answers = {
        q["id"]: q.get("correct_answer", "It outlines foundational definitions and architectural boundaries.")
        for q in questions
    }
    submit_res = await client.post(
        f"/api/v1/tutor/quizzes/{quiz_id}/submit",
        headers=user_a_headers,
        json={"answers": user_answers}
    )
    assert submit_res.status_code == 200
    s_data = submit_res.json()
    assert s_data["completed_at"] is not None
    assert "evaluation_results" in s_data
    eval_res = s_data["evaluation_results"]
    assert "score_pct" in eval_res
    assert eval_res["score_pct"] > 0
