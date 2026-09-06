import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_flashcard_generation_and_rating(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("flash_doc.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # 1. Generate Flashcards
    gen_res = await client.post(
        "/api/v1/tutor/flashcards/generate",
        headers=user_a_headers,
        json={"document_id": doc_id, "count": 3}
    )
    assert gen_res.status_code == 201
    cards = gen_res.json()
    assert len(cards) >= 1
    card_id = cards[0]["id"]
    assert "front" in cards[0]
    assert "back" in cards[0]
    assert "source_citations" in cards[0]

    # 2. List Flashcards
    list_res = await client.get(f"/api/v1/tutor/flashcards?document_id={doc_id}", headers=user_a_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Rate Flashcard
    rate_res = await client.post(
        f"/api/v1/tutor/flashcards/{card_id}/rate",
        headers=user_a_headers,
        json={"rating": "EASY"}
    )
    assert rate_res.status_code == 200
    assert rate_res.json()["review_rating"] == "EASY"
